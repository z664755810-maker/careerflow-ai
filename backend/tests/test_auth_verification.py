"""注册两步验证（邮箱验证码）测试。

默认无 SMTP 配置 → 开发态：request-code 直接返回 dev_code，不真发信。
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_request_code_dev_returns_code(client):
    r = await client.post(
        "/api/auth/register/request-code", json={"email": "new@test.com"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dev_code"] is not None
    assert len(body["dev_code"]) == 6


@pytest.mark.asyncio
async def test_verify_flow_creates_user(client):
    r = await client.post(
        "/api/auth/register/request-code", json={"email": "flow@test.com"}
    )
    code = r.json()["dev_code"]
    r2 = await client.post(
        "/api/auth/register/verify",
        json={"email": "flow@test.com", "code": code, "password": "password123"},
    )
    assert r2.status_code == 201
    assert r2.json()["email"] == "flow@test.com"


@pytest.mark.asyncio
async def test_verify_wrong_code_400(client):
    await client.post(
        "/api/auth/register/request-code", json={"email": "wrong@test.com"}
    )
    r = await client.post(
        "/api/auth/register/verify",
        json={"email": "wrong@test.com", "code": "000000", "password": "password123"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_request_code_existing_user_409(client):
    r = await client.post(
        "/api/auth/register/request-code", json={"email": "exists@test.com"}
    )
    code = r.json()["dev_code"]
    await client.post(
        "/api/auth/register/verify",
        json={"email": "exists@test.com", "code": code, "password": "password123"},
    )
    r2 = await client.post(
        "/api/auth/register/request-code", json={"email": "exists@test.com"}
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_cooldown_429(client):
    await client.post(
        "/api/auth/register/request-code", json={"email": "cool@test.com"}
    )
    r2 = await client.post(
        "/api/auth/register/request-code", json={"email": "cool@test.com"}
    )
    assert r2.status_code == 429
