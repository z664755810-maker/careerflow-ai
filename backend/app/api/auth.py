"""鉴权路由：注册（两步 + 邮箱验证码）/ 登录（JWT）/ 当前用户。"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, VerificationCode
from app.schemas import (
    RegisterCodeOut,
    RegisterRequest,
    RegisterVerify,
    Token,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from app.utils.email import send_verification_code

router = APIRouter(prefix="/auth", tags=["auth"])

CODE_TTL = timedelta(minutes=10)  # 验证码有效期
CODE_COOLDOWN = timedelta(seconds=60)  # 同邮箱重发冷却，避免刷爆邮件额度


def _now() -> datetime:
    """当前 UTC 时间（naive）。

    统一用 naive UTC 进行比较与存储：SQLite 读回的 DateTime(timezone=True)
    是 naive，PostgreSQL 的 timestamptz 在比较 naive 值时按 UTC 处理，
    二者行为一致，避免 aware/naive 比较抛 TypeError。
    """
    return datetime.utcnow()


def _naive(dt: datetime) -> datetime:
    """把数据库读回的 datetime 规整为 naive（SQLite 返回 naive，PG 返回 aware）。"""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


@router.post("/register/request-code", response_model=RegisterCodeOut)
async def request_code(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterCodeOut:
    """第一步：校验邮箱 → 生成 6 位验证码 → 存库 → 发信（或开发态返回）。

    开发态（未配置 SMTP）不真正发信，直接把验证码返回前端展示，保证演示站点零成本可走通。
    """
    exists = await db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")

    now = _now()
    # 冷却：60s 内已发过且未使用的码 → 拦截，防止刷爆免费邮件额度
    recent = await db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.email == payload.email,
            VerificationCode.purpose == "register",
        )
        .order_by(VerificationCode.created_at.desc())
    )
    if (
        recent is not None
        and not recent.used
        and _naive(recent.created_at) > now - CODE_COOLDOWN
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="验证码已发送，请稍后再试（60s）",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        VerificationCode(
            email=payload.email,
            code=code,
            purpose="register",
            expires_at=now + CODE_TTL,
        )
    )
    await db.commit()

    try:
        dev_code = await send_verification_code(payload.email, code)
    except Exception:
        # SMTP 已配置但发送失败 → 降级 503，不阻断注册流程的其余可用性
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="邮件服务暂不可用，请稍后再试",
        )

    if dev_code is not None:
        return RegisterCodeOut(dev_code=dev_code, message="演示模式：验证码已生成（见下方提示）")
    return RegisterCodeOut(dev_code=None, message="验证码已发送至邮箱，请查收（10 分钟内有效）")


@router.post("/register/verify", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def verify_register(payload: RegisterVerify, db: AsyncSession = Depends(get_db)) -> User:
    """第二步：校验验证码 → 创建用户。"""
    now = _now()
    row = await db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.email == payload.email,
            VerificationCode.purpose == "register",
            VerificationCode.used.is_(False),
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_at.desc())
    )
    if row is None or row.code != payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    row.used = True
    # 防并发重复建号
    if await db.scalar(select(User).where(User.email == payload.email)):
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")

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
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """返回当前登录用户基本信息。"""
    return current_user
