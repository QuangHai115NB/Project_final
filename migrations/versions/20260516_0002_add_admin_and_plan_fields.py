"""add admin and plan fields

Revision ID: 20260516_0002
Revises: 20260421_0001
Create Date: 2026-05-16 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_0002"
down_revision = "20260421_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=20), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"))
        batch_op.add_column(sa.Column("premium_until", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", server_default=None)
        batch_op.alter_column("plan", server_default=None)
        batch_op.alter_column("is_active", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_active")
        batch_op.drop_column("premium_until")
        batch_op.drop_column("plan")
        batch_op.drop_column("role")
