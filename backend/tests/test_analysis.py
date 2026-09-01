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


async def test_delete_analysis(client, monkeypatch):
    token = await _register_login(client, "del@example.com")
    rid, jid = await _make_resume_and_job(client, token)
    fake_json = '{"match_score": 80, "match_summary": "ok", "interview_questions": ["q1"]}'
    import app.api.analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "ask_llm", lambda *a, **k: fake_json)

    created = await client.post(
        "/api/analysis",
        json={"resume_id": rid, "job_id": jid},
        headers={"Authorization": f"Bearer {token}"},
    )
    aid = created.json()["id"]
    # 删除：应 204
    r = await client.delete(
        f"/api/analysis/{aid}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 204
    # 删除后查不到
    r = await client.get(
        "/api/analysis", headers={"Authorization": f"Bearer {token}"}
    )
    assert len(r.json()) == 0


async def test_delete_analysis_isolation(client, monkeypatch):
    t_a = await _register_login(client, "owner@example.com")
    rid, jid = await _make_resume_and_job(client, t_a)
    fake_json = '{"match_score": 70, "match_summary": "ok", "interview_questions": ["q1"]}'
    import app.api.analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "ask_llm", lambda *a, **k: fake_json)
    aid = (
        await client.post(
            "/api/analysis",
            json={"resume_id": rid, "job_id": jid},
            headers={"Authorization": f"Bearer {t_a}"},
        )
    ).json()["id"]

    # 用户 B 尝试删除 A 的记录：应 404（不暴露存在）
    t_b = await _register_login(client, "other@example.com")
    r = await client.delete(
        f"/api/analysis/{aid}", headers={"Authorization": f"Bearer {t_b}"}
    )
    assert r.status_code == 404

    # A 仍能查到（未被 B 删掉）
    r = await client.get(
        "/api/analysis", headers={"Authorization": f"Bearer {t_a}"}
    )
    assert len(r.json()) == 1
