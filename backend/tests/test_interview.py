"""模拟面试测试：鉴权 / 无 LLM 优雅降级 / 多轮评估落库 / 用户隔离。"""
from __future__ import annotations

import json

FAKE_ANALYSIS = (
    '{"match_score": 85, "skill_match": 88, "exp_match": 80, "education_match": 82, '
    '"salary_fit": 78, "match_summary": "ok", '
    '"interview_questions": ["请做自我介绍", "讲讲你遇到过最难的项目"]}'
)
FAKE_TURN = '{"score": 80, "feedback": "回答紧扣岗位，结构清晰", "next_question": "你为什么选择这个方向？"}'


async def _register_login(client, email):
    await client.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


async def _make_resume_job(client, token):
    h = {"Authorization": f"Bearer {token}"}
    rid = (
        await client.post("/api/resumes", json={"title": "简历", "content": "Python 后端"}, headers=h)
    ).json()["id"]
    jid = (
        await client.post("/api/jobs", json={"title": "后端", "description": "要求 Python"}, headers=h)
    ).json()["id"]
    return rid, jid


async def _make_analysis(client, token, monkeypatch, rid, jid):
    import app.api.analysis as am

    monkeypatch.setattr(am, "ask_llm", lambda *a, **k: FAKE_ANALYSIS)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/analysis", json={"resume_id": rid, "job_id": jid}, headers=h)
    return r.json()["id"]


async def test_interview_requires_auth(client):
    r = await client.post("/api/interview", json={"analysis_id": 1})
    assert r.status_code == 401


async def test_interview_start_no_llm_ok_but_answer_503(client, monkeypatch):
    token = await _register_login(client, "iv1@example.com")
    rid, jid = await _make_resume_job(client, token)
    aid = await _make_analysis(client, token, monkeypatch, rid, jid)
    h = {"Authorization": f"Bearer {token}"}

    # 开始面试不需要 LLM（首问来自分析里的面试题）
    s = await client.post("/api/interview", json={"analysis_id": aid}, headers=h)
    assert s.status_code == 201
    sid = s.json()["id"]

    # 作答时未 mock LLM（无 key）→ 优雅降级 503
    r = await client.post(
        f"/api/interview/{sid}/answer", json={"answer": "我的回答"}, headers=h
    )
    assert r.status_code == 503, r.text


async def test_interview_flow_with_mock(client, monkeypatch):
    token = await _register_login(client, "iv2@example.com")
    rid, jid = await _make_resume_job(client, token)
    aid = await _make_analysis(client, token, monkeypatch, rid, jid)
    import app.api.interview as ivm

    h = {"Authorization": f"Bearer {token}"}
    s = await client.post("/api/interview", json={"analysis_id": aid}, headers=h)
    assert s.status_code == 201
    sid = s.json()["id"]
    msgs = json.loads(s.json()["messages"])
    assert msgs[0]["role"] == "interviewer" and "自我介绍" in msgs[0]["content"]

    # mock 一轮 LLM 评估
    monkeypatch.setattr(ivm, "ask_llm", lambda *a, **k: FAKE_TURN)
    r = await client.post(
        f"/api/interview/{sid}/answer", json={"answer": "我是计算机专业应届生……"}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    msgs2 = json.loads(body["messages"])
    assert any(m["role"] == "candidate" for m in msgs2)
    assert body["current_score"] == 80.0
    assert body["status"] == "in_progress"  # 仍有下一题，会话继续
    assert "评价 80 分" in msgs2[-1]["content"]


async def test_interview_isolation(client, monkeypatch):
    t_a = await _register_login(client, "ivA@example.com")
    rid, jid = await _make_resume_job(client, t_a)
    aid = await _make_analysis(client, t_a, monkeypatch, rid, jid)
    ha = {"Authorization": f"Bearer {t_a}"}
    sid = (
        await client.post("/api/interview", json={"analysis_id": aid}, headers=ha)
    ).json()["id"]

    t_b = await _register_login(client, "ivB@example.com")
    hb = {"Authorization": f"Bearer {t_b}"}
    r = await client.get(f"/api/interview/{sid}", headers=hb)
    assert r.status_code == 404
    r2 = await client.delete(f"/api/interview/{sid}", headers=hb)
    assert r2.status_code == 404
