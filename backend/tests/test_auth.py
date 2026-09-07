"""鉴权测试：两步注册（验证码）/ 登录 / 当前用户 / 错误路径。"""
from __future__ import annotations


async def _register(client, email: str, password: str = "supersecret") -> None:
    """测试用：走两步注册（开发态验证码直接返回，无需邮件）。"""
    rc = await client.post("/api/auth/register/request-code", json={"email": email})
    code = rc.json()["dev_code"]
    r = await client.post(
        "/api/auth/register/verify",
        json={"email": email, "code": code, "password": password},
    )
    assert r.status_code == 201, r.text


async def test_register_and_me(client):
    await _register(client, "a@example.com")

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

    # 用户未泄露哈希
    r = await client.post(
        "/api/auth/register/verify",
        json={"email": "a@example.com", "code": "000000", "password": "x"},
    )
    # 该邮箱已注册（验证码错误也应先被邮箱已存在拦截，最终非 201）
    assert r.status_code != 201


async def test_duplicate_register_conflict(client):
    await _register(client, "dup@example.com")
    # 已注册邮箱再次请求验证码 → 409
    r = await client.post(
        "/api/auth/register/request-code", json={"email": "dup@example.com"}
    )
    assert r.status_code == 409


async def test_login_wrong_password(client):
    await _register(client, "b@example.com", "rightpass")
    r = await client.post(
        "/api/auth/login",
        data={"username": "b@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
