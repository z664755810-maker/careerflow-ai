# ============================================================
# CareerFlow AI · Render 部署镜像（多阶段，前后端同源托管）
# 构建上下文：仓库根目录（Render 默认读取仓库根 Dockerfile）
# 阶段1 构建前端 dist/，阶段2 跑后端并把 dist 拷入 /app/static
# 浏览器访问根路径即前端 UI，/api/* 归后端，免 CORS、一次部署两个服务
# ============================================================

# ---- 阶段1：构建前端 ----
FROM node:20-slim AS frontend-build
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- 阶段2：后端 ----
# 注：CareerFlow 不使用 Chroma / hnswlib，故可安全使用 3.13
# （RAG 项目锁 3.12 是受其 Chroma wheel 限制，与本项目无关）
FROM python:3.13-slim AS backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# 把前端构建产物拷入后端静态目录，由 FastAPI 同源托管
COPY --from=frontend-build /fe/dist ./static

ENV PORT=8000
EXPOSE 8000

# 直接读 $PORT 启动（见 backend/start.py），绕开 shell 展开
CMD ["python", "start.py"]
