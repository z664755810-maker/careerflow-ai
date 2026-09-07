"""add unique constraint on analyses (owner, resume, job)

Revision ID: 6e7f8091ab02
Revises: 5d6e7f8091ab
Create Date: 2026-09-07 19:40:00.000000

分析缓存去重：给 analyses 表加唯一索引 uq_analysis_owner_resume_job
(owner_id, resume_id, job_id)，保证同一用户同一「简历×JD」组合只有一条记录。
升级前先清理历史重复行（保留最新一条），避免唯一索引建不起来。
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '6e7f8091ab02'
down_revision: Union[str, None] = '5d6e7f8091ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # 安全网：清理历史重复 (owner_id, resume_id, job_id)，仅保留 id 最大（最新）的一条
    dup_rows = bind.execute(
        text(
            """
            SELECT owner_id, resume_id, job_id
            FROM analyses
            WHERE resume_id IS NOT NULL AND job_id IS NOT NULL
            GROUP BY owner_id, resume_id, job_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    for owner_id, resume_id, job_id in dup_rows:
        bind.execute(
            text(
                """
                DELETE FROM analyses
                WHERE owner_id = :o AND resume_id = :r AND job_id = :j
                  AND id NOT IN (
                    SELECT MAX(id) FROM analyses
                    WHERE owner_id = :o AND resume_id = :r AND job_id = :j
                  )
                """
            ),
            {"o": owner_id, "r": resume_id, "j": job_id},
        )

    op.create_index(
        'uq_analysis_owner_resume_job',
        'analyses',
        ['owner_id', 'resume_id', 'job_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_analysis_owner_resume_job', table_name='analyses')
