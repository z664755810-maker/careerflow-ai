"""FastAPI 依赖注入：当前用户解析与鉴权守卫。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# tokenUrl 指向登录接口，供 Swagger UI 的 "Authorize" 使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析出当前用户。

    Raises:
        HTTPException 401: token 缺失/无效/用户不存在。
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exc

    user = await db.scalar(select(User).where(User.id == int(subject)))
    if user is None:
        raise credentials_exc
    return user
