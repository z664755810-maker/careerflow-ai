"""add salary fields

Revision ID: 4c5d6e7f8091
Revises: 3b4c5d6e7f80
Create Date: 2026-09-01 15:50:00.000000

简历(resumes)加 expected_salary，JD(jobs)加 salary_range，用于 AI 薪资契合度评估有据可依。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8091'
down_revision: Union[str, None] = '3b4c5d6e7f80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resumes', sa.Column('expected_salary', sa.String(length=255), nullable=True))
    op.add_column('jobs', sa.Column('salary_range', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'salary_range')
    op.drop_column('resumes', 'expected_salary')
