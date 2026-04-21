"""add user profile fields

Revision ID: 20260421_0001
Revises:
Create Date: 2026-04-21 09:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("headline", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("bio", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("avatar_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("avatar_path")
        batch_op.drop_column("bio")
        batch_op.drop_column("headline")
        batch_op.drop_column("phone")
        batch_op.drop_column("full_name")
