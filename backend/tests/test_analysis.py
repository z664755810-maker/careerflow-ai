"""AI 分析测试：未配置 LLM 降级 + 正常解析落库 + 鉴权。"""
from __future__ import annotations


async def _register_login(client, email: str):
    await client.post(
        "/api/auth/register", json={"email": email, "password": "supersecret"}
    )
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


async def _make_resume_and_job(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    rid = (
        await client.post(
            "/api/resumes",
            json={"title": "简历", "content": "Python 后端开发"},
            headers=headers,
        )
    ).json()["id"]
    jid = (
        await client.post(
            "/api/jobs",
            json={"title": "后端工程师", "description": "要求 Python/FastAPI"},
            headers=headers,
        )
    ).json()["id"]
    return rid, jid


async def test_analysis_requires_auth(client):
    r = await client.post("/api/analysis", json={"resume_id": 1, "job_id": 1})
    assert r.status_code == 401


async def test_analysis_llm_unavailable_returns_503(client):
    token = await _register_login(client, "a1@example.com")
    rid, jid = await _make_resume_and_job(client, token)
    r = await client.post(
        "/api/analysis",
        json={"resume_id": rid, "job_id": jid},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 测试环境未配置 LLM，应优雅降级为 503
    assert r.status_code == 503, r.text


async def test_analysis_success(client, monkeypatch):
    token = await _register_login(client, "ok@example.com")
    rid, jid = await _make_resume_and_job(client, token)

    fake_json = (
        '{"match_score": 88, "match_summary": "匹配度较高", '
        '"interview_questions": ["讲讲 FastAPI 依赖注入", "如何做 JWT 鉴权"]}'
    )
    # 直接替换 analysis 模块内已绑定的 ask_llm 引用
    import app.api.analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "ask_llm", lambda *a, **k: fake_json)

    r = await client.post(
        "/api/analysis",
        json={"resume_id": rid, "job_id": jid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["match_score"] == 88
    assert body["match_summary"] == "匹配度较高"
    # interview_questions 以 JSON 字符串存储，这里验证可解析
    import json

    qs = json.loads(body["interview_questions"])
    assert isinstance(qs, list) and len(qs) == 2

    # 列表接口能查到历史
    r = await client.get(
        "/api/analysis", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200 and len(r.json()) == 1
