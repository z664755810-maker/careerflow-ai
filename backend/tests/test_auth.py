"""鉴权测试：注册 / 登录 / 当前用户 / 错误路径。"""
from __future__ import annotations


async def test_register_and_me(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "password": "supersecret"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "a@example.com"
    assert "id" in body and "hashed_password" not in body  # 不泄露哈希

    # 登录拿 token
    r = await client.post(
        "/api/auth/login",
        data={"username": "a@example.com", "password": "supersecret"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert token

    # /me 需鉴权
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


async def test_duplicate_register_conflict(client):
    payload = {"email": "dup@example.com", "password": "supersecret"}
    await client.post("/api/auth/register", json=payload)
    r = await client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "password": "rightpass"},
    )
    r = await client.post(
        "/api/auth/login",
        data={"username": "b@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
