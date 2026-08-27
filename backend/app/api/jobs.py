"""JD（职位描述）CRUD（按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Job, User
from app.schemas import JobCreate, JobOut, JobUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _get_owned_job(job_id: int, user: User, db: AsyncSession) -> Job:
    job = await db.get(Job, job_id)
    if job is None or job.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="JD 不存在")
    return job


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Job:
    job = Job(owner_id=user.id, title=payload.title, description=payload.description)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Job]:
    result = await db.scalars(
        select(Job).where(Job.owner_id == user.id).order_by(Job.created_at.desc())
    )
    return list(result)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Job:
    return await _get_owned_job(job_id, user, db)


@router.put("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: int,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Job:
    job = await _get_owned_job(job_id, user, db)
    if payload.title is not None:
        job.title = payload.title
    if payload.description is not None:
        job.description = payload.description
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    job = await _get_owned_job(job_id, user, db)
    await db.delete(job)
    await db.commit()
