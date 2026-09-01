"""Render / 通用 PaaS 启动入口。

要点：直接用 Python 读 `os.getenv("PORT")`，
绕开 `uvicorn app.main:app --port $PORT` 的 shell 展开写法
（部分 PaaS 的启动包装器对 $PORT 展开处理不一致，可能启动失败）。
"""
from __future__ import annotations

import os

import uvicorn

from app.main import app  # 复用已构造好的 FastAPI 实例（含 lifespan / 路由 / 中间件）


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
