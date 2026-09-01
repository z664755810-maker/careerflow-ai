"""add analysis dimension scores

Revision ID: 2a3b4c5d6e7f
Revises: 17ef322f6c5f
Create Date: 2026-09-01 00:00:00.000000

为 analyses 表新增四维匹配子分（skill_match / exp_match / education_match /
salary_fit），均为可空 FLOAT，兼容既有历史分析记录。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '17ef322f6c5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analyses', sa.Column('skill_match', sa.Float(), nullable=True))
    op.add_column('analyses', sa.Column('exp_match', sa.Float(), nullable=True))
    op.add_column('analyses', sa.Column('education_match', sa.Float(), nullable=True))
    op.add_column('analyses', sa.Column('salary_fit', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('analyses', 'salary_fit')
    op.drop_column('analyses', 'education_match')
    op.drop_column('analyses', 'exp_match')
    op.drop_column('analyses', 'skill_match')
