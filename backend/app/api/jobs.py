"""JD（职位描述）CRUD（按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Job, User
from app.schemas import JobCreate, JobOut, JobUpdate
from app.upload_utils import extract_text_from_file

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


@router.post("/upload", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def upload_job(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Job:
    """上传 JD 文件（.txt/.md/.pdf/.docx），自动解析文本并创建 JD。"""
    content = await file.read()
    try:
        text = extract_text_from_file(file.filename or "document.txt", content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="未能从文件中提取到文本内容"
        )
    name = (title or (file.filename or "未命名职位")).rsplit(".", 1)[0]
    job = Job(owner_id=user.id, title=name[:255], description=text[:50000])
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
