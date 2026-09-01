"""add interview_sessions

Revision ID: 3b4c5d6e7f80
Revises: 2a3b4c5d6e7f
Create Date: 2026-09-01 00:00:00.000000

新增模拟面试会话表 interview_sessions，持久化多轮面试对话与累计均分。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f80'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=True),
        sa.Column('analysis_title', sa.String(length=255), nullable=False),
        sa.Column('messages', sa.Text(), nullable=False),
        sa.Column('current_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interview_sessions_owner_id'), 'interview_sessions', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_interview_sessions_owner_id'), table_name='interview_sessions')
    op.drop_table('interview_sessions')
