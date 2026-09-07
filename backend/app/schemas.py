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


class RegisterRequest(BaseModel):
    """请求验证码：仅需邮箱。"""

    email: EmailStr


class RegisterVerify(BaseModel):
    """校验验证码并创建账号。"""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)


class RegisterCodeOut(BaseModel):
    """请求验证码的响应：开发态会携带 dev_code 供前端展示。"""

    dev_code: str | None = None
    message: str


# ---------- 简历 ----------
class ResumeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(default="", max_length=50000)
    expected_salary: str = Field(default="", max_length=255)


class ResumeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=50000)
    expected_salary: str | None = Field(default=None, max_length=255)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    content: str
    expected_salary: str = ""
    created_at: datetime
    updated_at: datetime


# ---------- JD ----------
class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=50000)
    salary_range: str = Field(default="", max_length=255)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=50000)
    salary_range: str | None = Field(default=None, max_length=255)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: str
    salary_range: str = ""
    created_at: datetime
    updated_at: datetime


# ---------- AI 分析 ----------
class AnalysisRequest(BaseModel):
    resume_id: int
    job_id: int
    # 强制重算：为 true 时忽略缓存、删除旧记录并重新调用 LLM 生成新结果；
    # 为 false（默认）时，若同一「简历×JD」已分析过则直接返回缓存，避免重复花销。
    force: bool = False


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    resume_id: int | None
    job_id: int | None
    match_score: float | None
    match_summary: str | None
    interview_questions: str | None  # JSON 字符串
    skill_match: float | None
    exp_match: float | None
    education_match: float | None
    salary_fit: float | None
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


# ---------- 模拟面试会话 ----------
class InterviewStart(BaseModel):
    analysis_id: int = Field(gt=0)


class InterviewAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class InterviewSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    analysis_id: int | None
    analysis_title: str
    messages: str  # JSON 字符串
    current_score: float | None
    status: str
    created_at: datetime
    updated_at: datetime
