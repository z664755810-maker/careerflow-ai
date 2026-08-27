"""FastAPI 应用入口：生命周期、CORS、路由装配。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, auth, jobs, resumes
from app.config import settings
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careerflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（生产可改用 Alembic；此处为零配置兜底）
    if settings.secret_key == "dev-only-secret-change-me-in-production":
        logger.warning("⚠️ 正在使用开发默认 SECRET_KEY，生产务必通过环境变量覆盖！")
    await init_db()
    logger.info("数据库已初始化（%s）", "SQLite" if settings.is_sqlite else "PostgreSQL")
    yield
    # 关闭：释放连接池
    from app.database import engine

    await engine.dispose()


app = FastAPI(title=settings.project_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(resumes.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"message": f"{settings.project_name} API. 文档见 /docs"}
