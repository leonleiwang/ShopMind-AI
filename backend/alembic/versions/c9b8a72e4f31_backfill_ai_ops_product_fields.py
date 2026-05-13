"""backfill_ai_ops_product_fields

Revision ID: c9b8a72e4f31
Revises: 7b4c6f2a1d22
Create Date: 2026-05-13 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9b8a72e4f31"
down_revision: Union[str, Sequence[str], None] = "7b4c6f2a1d22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE products SET pricing_suggestion = '' WHERE pricing_suggestion IS NULL")
    op.execute("UPDATE products SET marketing_copy = '' WHERE marketing_copy IS NULL")
    op.alter_column(
        "products",
        "pricing_suggestion",
        existing_type=sa.Text(),
        nullable=False,
        server_default="",
    )
    op.alter_column(
        "products",
        "marketing_copy",
        existing_type=sa.Text(),
        nullable=False,
        server_default="",
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "marketing_copy",
        existing_type=sa.Text(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "products",
        "pricing_suggestion",
        existing_type=sa.Text(),
        nullable=True,
        server_default=None,
    )
