"""add verification_codes

Revision ID: 5d6e7f8091ab
Revises: 4c5d6e7f8091
Create Date: 2026-09-07 19:30:00.000000

注册邮箱验证码表：支撑两步注册（请求验证码 → 校验验证码建号）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5d6e7f8091ab'
down_revision: Union[str, None] = '4c5d6e7f8091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'verification_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_verification_codes_email', 'verification_codes', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_verification_codes_email', table_name='verification_codes')
    op.drop_table('verification_codes')
