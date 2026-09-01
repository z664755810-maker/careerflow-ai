"""投递管理 CRUD（按用户隔离）。

投递 = 简历 × JD 的一次申请动作，跟踪状态：想投递 / 已投递 / 面试中 / 已拿offer / 已拒绝。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Application, Job, Resume, User
from app.schemas import APPLICATION_STATUSES, ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


async def _get_owned_app(app_id: int, user: User, db: AsyncSession) -> Application:
    app = await db.get(Application, app_id)
    if app is None or app.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投递记录不存在")
    return app


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Application:
    resume = await db.get(Resume, payload.resume_id)
    job = await db.get(Job, payload.job_id)
    if resume is None or resume.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    if job is None or job.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="JD 不存在")

    app = Application(
        owner_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
        resume_title=resume.title,
        job_title=job.title,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Application]:
    query = select(Application).where(Application.owner_id == user.id)
    if status:
        if status not in APPLICATION_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法状态过滤")
        query = query.where(Application.status == status)
    query = query.order_by(Application.created_at.desc())
    result = await db.scalars(query)
    return list(result)


@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Application:
    return await _get_owned_app(app_id, user, db)


@router.put("/{app_id}", response_model=ApplicationOut)
async def update_application(
    app_id: int,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Application:
    app = await _get_owned_app(app_id, user, db)
    if payload.status is not None:
        app.status = payload.status
    if payload.applied_at is not None:
        app.applied_at = payload.applied_at
    if payload.notes is not None:
        app.notes = payload.notes
    await db.commit()
    await db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    app = await _get_owned_app(app_id, user, db)
    await db.delete(app)
    await db.commit()
