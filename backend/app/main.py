"""FastAPI 应用入口：生命周期、CORS、路由装配、同源静态托管。"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analysis, applications, auth, interview, jobs, resumes
from app.config import settings
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careerflow")

# 静态资源目录：Docker 构建会把前端 dist 拷到 /app/static；本地开发无此目录则不启用同源托管。
STATIC_DIR = os.getenv("STATIC_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"
)
_HAS_FRONTEND = os.path.isdir(STATIC_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（SQLite 临时文件系统场景每次重启都会重建，随后由 seed 补数据）
    if settings.secret_key == "dev-only-secret-change-me-in-production":
        logger.warning("⚠️ 正在使用开发默认 SECRET_KEY，生产务必通过环境变量覆盖！")
    await init_db()
    logger.info("数据库已初始化（%s）", "SQLite" if settings.is_sqlite else "PostgreSQL")

    # 自动 seed：后台任务，不阻塞 uvicorn 启动（避免超 PaaS healthcheck 被判 unhealthy）
    # 仅由 AUTO_SEED 控制，与是否挂载前端静态目录解耦——
    # 否则 Docker/无前端目录下（如 Render）永远无法灌入演示数据，看板一进去是空的。
    if settings.auto_seed:
        from app.seed import _auto_seed

        asyncio.create_task(_auto_seed())

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
app.include_router(applications.router, prefix=settings.api_prefix)
app.include_router(interview.router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


if _HAS_FRONTEND:
    # 同源托管：前端 build 产物由后端直接服务，根路径即 UI，/api 仍归后端（免 CORS）。
    # 该 catch-all 在路由注册最后添加，/api、/docs、/health 等已注册路由优先匹配。
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        # API 路径不应被 SPA 兜底拦截：返回 404 JSON 而非 HTML，
        # 避免客户端（或带斜杠/拼写错误的请求）误收到首页页面。
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # 静态资源（如 /assets/index-xxx.js）若存在则直接返回文件
        candidate = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        # 其余路径（含 SPA 深链 /resumes）回退到 index.html，交给前端路由处理
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

else:
    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"message": f"{settings.project_name} API. 文档见 /docs"}
