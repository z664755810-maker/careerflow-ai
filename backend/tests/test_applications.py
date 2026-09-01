"""投递管理 API 测试：CRUD + 用户隔离。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal
from app.main import app
from app.models import Job, Resume
from tests.conftest import _login, _make_user


@pytest.mark.asyncio
async def test_application_crud_and_isolation(client):
    # 准备两个用户，各自简历/JD
    async with AsyncSessionLocal() as db:
        u1 = await _make_user(db, "apps1@test.com", "password123")
        await _make_user(db, "apps2@test.com", "password123")
        r1 = Resume(owner_id=u1.id, title="简历A", content="x")
        j1 = Job(owner_id=u1.id, title="JD A", description="y")
        db.add_all([r1, j1])
        await db.commit()
        await db.refresh(r1)
        await db.refresh(j1)

    t1 = await _login("apps1@test.com", "password123")
    t2 = await _login("apps2@test.com", "password123")
    headers1 = {"Authorization": f"Bearer {t1}"}
    headers2 = {"Authorization": f"Bearer {t2}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 创建投递
        r = await client.post(
            "/api/applications",
            json={"resume_id": r1.id, "job_id": j1.id, "status": "applied", "notes": "内推"},
            headers=headers1,
        )
        assert r.status_code == 201, r.text
        app_id = r.json()["id"]
        assert r.json()["resume_title"] == "简历A" and r.json()["job_title"] == "JD A"

        # 列表
        r = await client.get("/api/applications", headers=headers1)
        assert r.status_code == 200 and len(r.json()) == 1

        # 按状态过滤
        r = await client.get("/api/applications?status=interview", headers=headers1)
        assert r.status_code == 200 and len(r.json()) == 0

        # 非法状态
        r = await client.post(
            "/api/applications",
            json={"resume_id": r1.id, "job_id": j1.id, "status": "hacked"},
            headers=headers1,
        )
        assert r.status_code == 422

        # 更新状态 + applied_at
        r = await client.put(
            f"/api/applications/{app_id}",
            json={"status": "offer", "notes": "已 offer"},
            headers=headers1,
        )
        assert r.status_code == 200 and r.json()["status"] == "offer"

        # u2 越权访问应 404
        r = await client.get(f"/api/applications/{app_id}", headers=headers2)
        assert r.status_code == 404
        r = await client.delete(f"/api/applications/{app_id}", headers=headers2)
        assert r.status_code == 404

        # u1 删除
        r = await client.delete(f"/api/applications/{app_id}", headers=headers1)
        assert r.status_code == 204
        r = await client.get("/api/applications", headers=headers1)
        assert len(r.json()) == 0


@pytest.mark.asyncio
async def test_application_rejects_missing_resume(client):
    async with AsyncSessionLocal() as db:
        await _make_user(db, "apps3@test.com", "password123")
        await db.commit()
    token = await _login("apps3@test.com", "password123")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/applications",
            json={"resume_id": 99999, "job_id": 99999},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404
