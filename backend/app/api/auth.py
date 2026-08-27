"""鉴权路由：注册 / 登录（JWT）/ 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """注册新用户。邮箱唯一，密码做加盐哈希。"""
    exists = await db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册"
        )

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),  # username=邮箱, password=密码
    db: AsyncSession = Depends(get_db),
) -> Token:
    """密码登录，返回 JWT。"""
    user = await db.scalar(select(User).where(User.email == form.username))
    # 统一错误文案，避免泄露邮箱是否存在
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """返回当前登录用户基本信息。"""
    return current_user
