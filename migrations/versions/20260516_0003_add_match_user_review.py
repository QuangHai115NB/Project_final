"""add match user review

Revision ID: 20260516_0003
Revises: 20260516_0002
Create Date: 2026-05-16 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_0003"
down_revision = "20260516_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("match_history") as batch_op:
        batch_op.add_column(sa.Column("user_review", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("match_history") as batch_op:
        batch_op.drop_column("user_review")
