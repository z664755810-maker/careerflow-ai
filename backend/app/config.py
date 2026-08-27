"""应用配置（pydantic-settings）。

所有敏感配置只走环境变量，绝不硬编码密钥。
数据库 URL 可切换：
- 本地开发/测试：SQLite（无需额外服务，开箱即跑）
- 生产（Render + docker-compose）：PostgreSQL（asyncpg）
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行时配置。字段从环境变量或 .env 读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ----- 数据库 -----
    # 默认 SQLite，方便本地零依赖起项目；生产改为 Postgres 异步 URL
    database_url: str = "sqlite+aiosqlite:///./careerflow.db"

    # ----- JWT -----
    # 生产务必通过环境变量覆盖；这里仅作本地开发兜底（会在日志中告警）
    secret_key: str = "dev-only-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # ----- LLM（OpenAI 兼容，key 只走环境变量）-----
    llm_api_key: str = ""
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"  # 智谱，免费 glm-4-flash
    llm_model: str = "glm-4-flash"

    # ----- 应用 -----
    project_name: str = "CareerFlow AI"
    api_prefix: str = "/api"
    # CORS：生产把前端 Vercel 域名加进来，多个用逗号分隔
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


@lru_cache
def get_settings() -> Settings:
    """缓存配置单例（避免每次请求重复解析环境变量）。"""
    return Settings()


settings = get_settings()
