"""简历 CRUD 测试：鉴权守卫与用户隔离。"""
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


async def test_create_and_list_resume(client):
    token = await _register_login(client, "r1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/resumes",
        json={"title": "我的简历", "content": "熟悉 Python 与 FastAPI。"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    r = await client.get("/api/resumes", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == rid


async def test_resume_requires_auth(client):
    r = await client.post(
        "/api/resumes", json={"title": "x", "content": "y"}
    )
    assert r.status_code == 401


async def test_user_isolation(client):
    t_a = await _register_login(client, "a1@example.com")
    t_b = await _register_login(client, "b1@example.com")
    h_a = {"Authorization": f"Bearer {t_a}"}
    h_b = {"Authorization": f"Bearer {t_b}"}

    r = await client.post(
        "/api/resumes",
        json={"title": "A 的简历", "content": "..."},
        headers=h_a,
    )
    rid = r.json()["id"]

    # B 看不到，也不能改/删 A 的
    assert (await client.get("/api/resumes", headers=h_b)).json() == []
    assert (await client.get(f"/api/resumes/{rid}", headers=h_b)).status_code == 404
    assert (
        await client.delete(f"/api/resumes/{rid}", headers=h_b)
    ).status_code == 404


async def test_update_and_delete_resume(client):
    token = await _register_login(client, "u1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    rid = (
        await client.post(
            "/api/resumes",
            json={"title": "旧标题", "content": "旧内容"},
            headers=headers,
        )
    ).json()["id"]

    r = await client.put(
        f"/api/resumes/{rid}",
        json={"title": "新标题", "content": "新内容"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "新标题"

    r = await client.delete(f"/api/resumes/{rid}", headers=headers)
    assert r.status_code == 204
    assert (await client.get(f"/api/resumes/{rid}", headers=headers)).status_code == 404
