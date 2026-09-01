"""简历 CRUD（按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Resume, User
from app.schemas import ResumeCreate, ResumeOut, ResumeUpdate
from app.upload_utils import extract_text_from_file

router = APIRouter(prefix="/resumes", tags=["resumes"])


async def _get_owned_resume(resume_id: int, user: User, db: AsyncSession) -> Resume:
    """取属于当前用户的简历，否则 404。"""
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="简历不存在")
    return resume


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def create_resume(
    payload: ResumeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Resume:
    resume = Resume(
        owner_id=user.id,
        title=payload.title,
        content=payload.content,
        expected_salary=payload.expected_salary or "",
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut])
async def list_resumes(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Resume]:
    result = await db.scalars(
        select(Resume).where(Resume.owner_id == user.id).order_by(Resume.created_at.desc())
    )
    return list(result)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Resume:
    return await _get_owned_resume(resume_id, user, db)


@router.put("/{resume_id}", response_model=ResumeOut)
async def update_resume(
    resume_id: int,
    payload: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Resume:
    resume = await _get_owned_resume(resume_id, user, db)
    if payload.title is not None:
        resume.title = payload.title
    if payload.content is not None:
        resume.content = payload.content
    if payload.expected_salary is not None:
        resume.expected_salary = payload.expected_salary
    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    resume = await _get_owned_resume(resume_id, user, db)
    await db.delete(resume)
    await db.commit()


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Resume:
    """上传简历文件（.txt/.md/.pdf/.docx），自动解析文本并创建简历。"""
    content = await file.read()
    try:
        text = extract_text_from_file(file.filename or "document.txt", content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="未能从文件中提取到文本内容"
        )
    name = (title or (file.filename or "未命名简历")).rsplit(".", 1)[0]
    resume = Resume(owner_id=user.id, title=name[:255], content=text[:50000])
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume
