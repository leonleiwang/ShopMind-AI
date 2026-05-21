"""add user role

Revision ID: b8f3a6d41c2e
Revises: a4d2e7c9f801
Create Date: 2026-05-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b8f3a6d41c2e"
down_revision = "a4d2e7c9f801"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="shopper"))
    op.execute("UPDATE users SET role = 'admin' WHERE is_superuser = true")
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
