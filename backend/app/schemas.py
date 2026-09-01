"""Pydantic v2 请求/响应模型。

输入做校验（email 格式、长度限制），输出做字段筛选（不泄露密码哈希）。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# 投递状态：想投递 / 已投递 / 面试中 / 已拿offer / 已拒绝
APPLICATION_STATUSES = ["wishlist", "applied", "interview", "offer", "rejected"]


def _validate_status(v: str | None) -> str | None:
    if v is not None and v not in APPLICATION_STATUSES:
        raise ValueError(f"非法状态：{v}")
    return v


# ---------- 用户 / 鉴权 ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 简历 ----------
class ResumeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=50000)


class ResumeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=50000)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


# ---------- JD ----------
class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=50000)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=50000)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: str
    created_at: datetime
    updated_at: datetime


# ---------- AI 分析 ----------
class AnalysisRequest(BaseModel):
    resume_id: int
    job_id: int


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    resume_id: int | None
    job_id: int | None
    match_score: float | None
    match_summary: str | None
    interview_questions: str | None  # JSON 字符串
    created_at: datetime


# ---------- 投递管理 ----------
class ApplicationCreate(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    status: str = "wishlist"
    notes: str = Field(default="", max_length=5000)

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        _validate_status(v)
        return v


class ApplicationUpdate(BaseModel):
    status: str | None = None
    applied_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        return _validate_status(v)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    resume_id: int | None
    job_id: int | None
    resume_title: str
    job_title: str
    status: str
    applied_at: datetime | None
    notes: str
    created_at: datetime
    updated_at: datetime
