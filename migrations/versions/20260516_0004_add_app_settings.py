"""add app settings

Revision ID: 20260516_0004
Revises: 20260516_0003
Create Date: 2026-05-16 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_0004"
down_revision = "20260516_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
