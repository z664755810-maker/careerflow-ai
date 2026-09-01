"""异步数据库引擎与会话（SQLAlchemy 2.0 async）。

设计要点：
- 同时兼容 SQLite(aiosqlite) 与 PostgreSQL(asyncpg)，模型层保持可移植。
- get_db 以依赖注入方式提供事务会话，请求结束自动关闭。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""


def _make_engine():
    """根据 database_url 构造异步引擎。

    SQLite 需要关闭单连接检查，PostgreSQL 用连接池。
    """
    if settings.is_sqlite:
        # SQLite 异步下必须允许跨协程复用连接
        return create_async_engine(
            settings.database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=None,  # SQLite 默认使用 SingletonThreadPool
        )
    # PostgreSQL：标准异步连接池
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


engine = _make_engine()

# async sessionmaker：expire_on_commit=False 避免在响应序列化后访问已过期属性
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每个请求一个会话，结束后回滚/关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """建表（开发引导用）。

    生产推荐用 Alembic 迁移（见 migrations/），此处作为零配置兜底。
    """
    # 延迟导入，避免循环依赖
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 轻量迁移：为已存在的旧表补加新增列（create_all 不会给旧表加列）。
    # 用 inspector 检查，缺列才 ALTER ADD COLUMN，幂等且跨 SQLite/Postgres 通用。
    await _ensure_analysis_dimension_columns()
    await _ensure_salary_columns()


async def _ensure_analysis_dimension_columns() -> None:
    """为 analyses 表补齐四维匹配子分列（若缺失）。

    仅当列不存在时才执行 ALTER，避免重复执行报错；保持与模型定义同步。
    """
    expected = {
        "skill_match": "FLOAT",
        "exp_match": "FLOAT",
        "education_match": "FLOAT",
        "salary_fit": "FLOAT",
    }
    async with engine.begin() as conn:
        existing = await conn.run_sync(
            lambda sync_conn: {c["name"] for c in inspect(sync_conn).get_columns("analyses")}
        )
        for col, col_type in expected.items():
            if col not in existing:
                await conn.execute(text(f"ALTER TABLE analyses ADD COLUMN {col} {col_type}"))


async def _ensure_salary_columns() -> None:
    """为 resumes / jobs 表补齐薪资列（若缺失），保证旧库升级不丢数据。"""
    salary_cols = {
        "resumes": {"expected_salary": "VARCHAR(255)"},
        "jobs": {"salary_range": "VARCHAR(255)"},
    }
    async with engine.begin() as conn:
        for table, cols in salary_cols.items():
            existing = await conn.run_sync(
                lambda sync_conn, t=table: {c["name"] for c in inspect(sync_conn).get_columns(t)}
            )
            for col, col_type in cols.items():
                if col not in existing:
                    await conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT ''")
                    )
