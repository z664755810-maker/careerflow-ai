"""AI 分析路由：简历 × JD 匹配度 + 模拟面试问题（Agent 式 LLM 调用）。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.llm import ask_llm
from app.models import Analysis, Job, Resume, User
from app.schemas import AnalysisOut, AnalysisRequest

router = APIRouter(prefix="/analysis", tags=["analysis"])

_SYSTEM_PROMPT = (
    "你是一位资深的校招 HR 与技术面试官，擅长评估候选人与岗位的匹配度。"
    "请基于给定的简历与职位描述，输出严格合法的 JSON（不要包含任何解释文字或 markdown 代码块），"
    "结构如下：\n"
    '{\n'
    '  "match_score": 0到100的整数，表示综合匹配度,\n'
    '  "skill_match": 0到100的整数，技能匹配度（岗位要求技能与简历技能的契合）,\n'
    '  "exp_match": 0到100的整数，经验匹配度（相关项目/实习经历与岗位的契合）,\n'
    '  "education_match": 0到100的整数，学历匹配度（学历/专业与岗位要求的契合）,\n'
    '  "salary_fit": 0到100的整数，薪资契合度（岗位薪资区间与候选人期望的契合，无明确信息时给合理估算）,\n'
    '  "match_summary": "3-5句中文分析，指出优势与差距",\n'
    '  "interview_questions": ["3-5个针对该候选人与岗位的模拟面试问题，具体且可考察能力"]\n'
    "}\n"
    "只输出 JSON。"
)

# 四个分维度字段名（与模型/库一致），用于解析与落库
_DIMENSION_KEYS = ("skill_match", "exp_match", "education_match", "salary_fit")


def _to_score(v) -> float | None:
    """把 LLM 返回的分值统一成 0-100 的 float；非法/缺失返回 None。"""
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


def _parse_llm_output(raw: str) -> dict:
    """解析 LLM 返回的 JSON，尽量容错。

    先从可能的 ```json 代码块中提取，再整体解析；打分夹带单位/符号也尝试提取数字。
    """
    text = raw.strip()
    if text.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "match_score": None,
            "match_summary": raw,
            "interview_questions": [],
            "skill_match": None,
            "exp_match": None,
            "education_match": None,
            "salary_fit": None,
        }

    score = _to_score(data.get("match_score"))

    questions = data.get("interview_questions", [])
    if not isinstance(questions, list):
        questions = [str(questions)]

    summary = data.get("match_summary")
    result = {
        "match_score": score,
        "match_summary": summary if isinstance(summary, str) else None,
        "interview_questions": [str(q) for q in questions],
    }
    # 四个分维度子分
    for key in _DIMENSION_KEYS:
        result[key] = _to_score(data.get(key))
    return result


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def analyze(
    payload: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Analysis:
    """对指定简历与 JD 做 AI 匹配分析，结果落库。"""
    resume = await db.get(Resume, payload.resume_id)
    job = await db.get(Job, payload.job_id)
    if resume is None or resume.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if job is None or job.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="JD 不存在")

    user_prompt = (
        f"【简历】\n标题：{resume.title}\n内容：\n{resume.content}\n\n"
        f"【职位描述】\n标题：{job.title}\n内容：\n{job.description}\n"
    )

    raw = ask_llm(_SYSTEM_PROMPT, user_prompt, max_tokens=1200, temperature=0.4)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置或调用失败：请在环境变量设置 LLM_API_KEY（推荐智谱 glm-4-flash 免费）。",
        )

    parsed = _parse_llm_output(raw)
    record = Analysis(
        owner_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
        match_score=parsed["match_score"],
        match_summary=parsed["match_summary"],
        interview_questions=json.dumps(parsed["interview_questions"], ensure_ascii=False),
        skill_match=parsed["skill_match"],
        exp_match=parsed["exp_match"],
        education_match=parsed["education_match"],
        salary_fit=parsed["salary_fit"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("", response_model=list[AnalysisOut])
async def list_analyses(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Analysis]:
    result = await db.scalars(
        select(Analysis)
        .where(Analysis.owner_id == user.id)
        .order_by(Analysis.created_at.desc())
    )
    return list(result)


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Analysis:
    record = await db.get(Analysis, analysis_id)
    if record is None or record.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")
    return record


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """删除指定分析记录（仅本人可删，越权返回 404）。"""
    record = await db.get(Analysis, analysis_id)
    if record is None or record.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")
    await db.delete(record)
    await db.commit()
