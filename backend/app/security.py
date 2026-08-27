"""密码哈希与 JWT 工具。

密码哈希：passlib 的 pbkdf2_sha256 方案（纯 Python、跨平台零原生依赖，
在 Python 3.13 上比 bcrypt 更少踩坑；本项目规模下安全性完全够用）。
JWT：python-jose 签发 HS256 token，密钥来自配置（生产必须走环境变量）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# 仅使用 pbkdf2_sha256，避免 bcrypt 在部分环境的兼容性问题
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码做加盐哈希。"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文与哈希是否匹配。"""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """签发 JWT。

    Args:
        subject: 通常放用户 id（转为字符串）。
        expires_minutes: 过期分钟数；缺省用配置值。

    Returns:
        编码后的 JWT 字符串。
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    # 标准 claim：sub + exp
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """解码 JWT，返回 subject（用户 id 字符串）；无效则返回 None。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
