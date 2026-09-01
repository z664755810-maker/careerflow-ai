"""模拟面试路由：基于某次 AI 分析，开启一轮多轮面试对话。

流程：开始面试（用分析里的面试题作首问）→ 候选人逐轮作答 →
后端调用 LLM 评价打分并给出下一题 → 累计均分。无 LLM key 时优雅降级为 503。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.llm import ask_llm
from app.models import Analysis, InterviewSession, Job, Resume, User
from app.schemas import InterviewAnswer, InterviewSessionOut, InterviewStart

router = APIRouter(prefix="/interview", tags=["interview"])


_SYSTEM_PROMPT = (
    "你是一位严格的校招技术面试官，擅长基于简历与职位评估候选人。"
    "请基于给定的简历、职位描述与已进行的面试对话，做两件事并输出严格合法 JSON"
    "（不要包含 markdown 代码块或解释文字）：\n"
    "1) evaluate：对候选人「上一条回答」给出 0-100 的整数分数与 2-3 句中文反馈；\n"
    "2) next_question：提出一个针对该候选人与岗位的下一个面试问题；"
    "若已经过 3-4 轮或候选人表现足以结束，可返回 null 表示面试结束。\n"
    '结构：{"score": int, "feedback": "str", "next_question": "str 或 null"}\n只输出 JSON。'
)


def _to_score(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, str):
        digits = "".join(ch for ch in v if ch.isdigit() or ch == ".")
        v = float(digits) if digits else None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return max(0.0, min(100.0, float(v)))
    return None


def _parse_turn(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"score": None, "feedback": raw, "next_question": None}

    feedback = data.get("feedback")
    nq = data.get("next_question")
    return {
        "score": _to_score(data.get("score")),
        "feedback": feedback if isinstance(feedback, str) else "",
        "next_question": nq if isinstance(nq, str) and nq.strip() else None,
    }


async def _titles(db, analysis: Analysis) -> tuple[str, str]:
    """取简历/JD 标题用于会话快照（源被删也不影响，取不到就用占位）。"""
    resume_title = job_title = ""
    if analysis.resume_id:
        r = await db.get(Resume, analysis.resume_id)
        if r:
            resume_title = r.title
    if analysis.job_id:
        j = await db.get(Job, analysis.job_id)
        if j:
            job_title = j.title
    return resume_title, job_title


@router.post("", response_model=InterviewSessionOut, status_code=status.HTTP_201_CREATED)
async def start_interview(
    payload: InterviewStart,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewSession:
    """基于某次分析开启一轮模拟面试，首问取自该分析的面试题。"""
    analysis = await db.get(Analysis, payload.analysis_id)
    if analysis is None or analysis.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")

    questions: list[str] = []
    if analysis.interview_questions:
        try:
            questions = [str(q) for q in json.loads(analysis.interview_questions)]
        except json.JSONDecodeError:
            questions = []
    first_q = questions[0] if questions else "请做一个简短的自我介绍，并说明你为什么适合这个岗位。"

    resume_title, job_title = await _titles(db, analysis)
    snapshot = f"{resume_title or '简历'} × {job_title or 'JD'}" if (resume_title or job_title) else f"分析 #{analysis.id}"

    session = InterviewSession(
        owner_id=user.id,
        analysis_id=analysis.id,
        analysis_title=snapshot,
        messages=json.dumps(
            [{"role": "interviewer", "content": first_q, "score": None}], ensure_ascii=False
        ),
        status="in_progress",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[InterviewSessionOut])
async def list_interviews(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[InterviewSession]:
    result = await db.scalars(
        select(InterviewSession)
        .where(InterviewSession.owner_id == user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    return list(result)


@router.get("/{session_id}", response_model=InterviewSessionOut)
async def get_interview(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewSession:
    session = await db.get(InterviewSession, session_id)
    if session is None or session.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    return session


@router.post("/{session_id}/answer", response_model=InterviewSessionOut)
async def answer_interview(
    session_id: int,
    payload: InterviewAnswer,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewSession:
    """提交一轮作答：LLM 评价打分 + 出下一题，更新会话与累计均分。"""
    session = await db.get(InterviewSession, session_id)
    if session is None or session.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="面试已结束")

    history = json.loads(session.messages)
    history.append({"role": "candidate", "content": payload.answer, "score": None})

    # 组装上下文：简历内容 + JD 描述 + 对话记录
    resume_text = job_text = ""
    if session.analysis_id:
        analysis = await db.get(Analysis, session.analysis_id)
        if analysis:
            if analysis.resume_id:
                r = await db.get(Resume, analysis.resume_id)
                if r:
                    resume_text = r.content
            if analysis.job_id:
                j = await db.get(Job, analysis.job_id)
                if j:
                    job_text = j.description

    transcript = "\n".join(
        f"【{'面试官' if m['role'] == 'interviewer' else '候选人'}】{m['content']}" for m in history
    )
    user_prompt = (
        f"【简历】\n{resume_text or '（无）'}\n\n"
        f"【职位描述】\n{job_text or '（无）'}\n\n"
        f"【已进行的面试对话】\n{transcript}\n\n"
        "请评价候选人「最后一条（候选人）回答」，并给出下一个面试问题（或返回 null 结束）。"
    )

    raw = ask_llm(_SYSTEM_PROMPT, user_prompt, max_tokens=900, temperature=0.5)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置或调用失败：请在环境变量设置 LLM_API_KEY。",
        )

    turn = _parse_turn(raw)
    score_val = turn["score"]
    score_text = (
        str(int(score_val)) if score_val is not None and float(score_val).is_integer() else str(score_val)
    )
    head = f"【评价 {score_text} 分】{turn['feedback']}" if turn["score"] is not None else turn["feedback"]
    tail = f"\n\n下一题：{turn['next_question']}" if turn["next_question"] else "\n\n（面试到此结束，感谢参与。）"
    history.append({"role": "interviewer", "content": head + tail, "score": turn["score"]})

    session.messages = json.dumps(history, ensure_ascii=False)
    scores = [m["score"] for m in history if isinstance(m.get("score"), (int, float))]
    session.current_score = round(sum(scores) / len(scores), 1) if scores else None
    if turn["next_question"] is None:
        session.status = "completed"
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    session = await db.get(InterviewSession, session_id)
    if session is None or session.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面试会话不存在")
    await db.delete(session)
    await db.commit()
