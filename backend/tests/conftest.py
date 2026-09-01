"""测试夹具：独立 SQLite 测试库 + httpx 异步客户端。

要点：
- 必须在导入 app 之前设置 DATABASE_URL，否则 engine 会用默认库。
- 不配置 LLM（LLM_API_KEY 为空），分析接口应返回 503，体现优雅降级。
- 每个测试后清空所有表，保证用例间相互隔离。
"""
from __future__ import annotations

import os

# 先于任何 app 导入执行。
# 默认用 SQLite 测试库；若 CI 设置了 DATABASE_URL（如 Postgres 服务容器），则优先使用，
# 这样同一套测试既能本地零依赖跑，也能在 CI 中对真实 PostgreSQL 验证可移植性。
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_careerflow.db")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["LLM_API_KEY"] = ""
# 测试不希望被自动 seed 灌入演示数据
os.environ["AUTO_SEED"] = "0"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    yield
    async with AsyncSessionLocal() as session:
        # 先删子表再删父表，避免外键约束冲突
        for table in ("analyses", "applications", "resumes", "jobs", "users"):
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()


async def _make_user(db, email: str, password: str) -> User:
    """测试用：创建用户并返回 ORM 对象（已 flush，含 id）。"""
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()
    return user


async def _login(email: str, password: str) -> str:
    """测试用：登录并返回 access_token。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        return r.json()["access_token"]
