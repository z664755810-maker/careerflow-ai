"""AI 分析测试：未配置 LLM 降级 + 正常解析落库 + 鉴权。"""
from __future__ import annotations


async def _register_login(client, email: str, password: str = "supersecret"):
    rc = await client.post("/api/auth/register/request-code", json={"email": email})
    code = rc.json()["dev_code"]
    await client.post(
        "/api/auth/register/verify",
        json={"email": email, "code": code, "password": password},
    )
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": password}
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
        '{"match_score": 88, "skill_match": 90, "exp_match": 88, '
        '"education_match": 85, "salary_fit": 80, '
        '"match_summary": "匹配度较高", '
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
    # 四维子分应随记录返回
    assert body["skill_match"] == 90
    assert body["exp_match"] == 88
    assert body["education_match"] == 85
    assert body["salary_fit"] == 80
    # interview_questions 以 JSON 字符串存储，这里验证可解析
    import json

    qs = json.loads(body["interview_questions"])
    assert isinstance(qs, list) and len(qs) == 2

    # 列表接口能查到历史
    r = await client.get(
        "/api/analysis", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200 and len(r.json()) == 1


async def test_parse_llm_output_dimensions(client):
    """解析容错：分维度子分做 0-100 钳制、去单位、null/缺失置 None。"""
    import app.api.analysis as analysis_mod

    parsed = analysis_mod._parse_llm_output(
        '{"match_score": 120, "skill_match": 130, "exp_match": "85分", '
        '"education_match": null, "salary_fit": 70, '
        '"match_summary": "ok", "interview_questions": ["q1"]}'
    )
    assert parsed["match_score"] == 100.0  # 综合分钳制到 100
    assert parsed["skill_match"] == 100.0  # 子分同样钳制
    assert parsed["exp_match"] == 85.0  # 去"分"单位
    assert parsed["education_match"] is None  # null -> None
    assert parsed["salary_fit"] == 70.0


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


async def test_analysis_dedup_returns_cache(client, monkeypatch):
    """缓存去重：同一「简历×JD」第二次请求应命中缓存(200)且不再新增记录。"""
    import app.api.analysis as analysis_mod

    token = await _register_login(client, "dedup@example.com")
    rid, jid = await _make_resume_and_job(client, token)
    calls = {"n": 0}

    def _fake(*a, **k):
        calls["n"] += 1
        return (
            '{"match_score": 88, "skill_match": 90, "exp_match": 80, '
            '"education_match": 85, "salary_fit": 82, '
            '"match_summary": "ok", "interview_questions": ["q1"]}'
        )

    monkeypatch.setattr(analysis_mod, "ask_llm", _fake)
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.post("/api/analysis", json={"resume_id": rid, "job_id": jid}, headers=headers)
    assert r1.status_code == 201, r1.text
    id1 = r1.json()["id"]

    # 同一组合再次分析：应命中缓存返回 200，且 LLM 不再被调用（calls 仍为 1）
    r2 = await client.post("/api/analysis", json={"resume_id": rid, "job_id": jid}, headers=headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == id1  # 返回的是同一条缓存记录
    assert calls["n"] == 1, "命中缓存后不应再次调用 LLM"

    # 历史列表仍只有 1 条（去重生效）
    lst = await client.get("/api/analysis", headers=headers)
    assert len(lst.json()) == 1


async def test_analysis_force_recalc(client, monkeypatch):
    """强制重算：force=true 应删除旧记录并生成新结果，历史仍只有 1 条。"""
    import app.api.analysis as analysis_mod

    token = await _register_login(client, "force@example.com")
    rid, jid = await _make_resume_and_job(client, token)
    seq = [
        '{"match_score": 70, "match_summary": "old", "interview_questions": ["q1"]}',
        '{"match_score": 95, "match_summary": "new", "interview_questions": ["q1"]}',
    ]
    it = iter(seq)

    def _fake(*a, **k):
        return next(it)

    monkeypatch.setattr(analysis_mod, "ask_llm", _fake)
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.post("/api/analysis", json={"resume_id": rid, "job_id": jid}, headers=headers)
    assert r1.status_code == 201 and r1.json()["match_score"] == 70

    r2 = await client.post(
        "/api/analysis",
        json={"resume_id": rid, "job_id": jid, "force": True},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["match_score"] == 95  # 新生成的结果

    # 强制重算后，旧记录被替换，历史仍只有 1 条
    lst = await client.get("/api/analysis", headers=headers)
    assert len(lst.json()) == 1
    assert lst.json()[0]["match_score"] == 95
