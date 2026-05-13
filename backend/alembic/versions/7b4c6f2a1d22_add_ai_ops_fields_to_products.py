"""add_ai_ops_fields_to_products

Revision ID: 7b4c6f2a1d22
Revises: e6d1c2e1e0fb
Create Date: 2026-05-13 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b4c6f2a1d22"
down_revision: Union[str, Sequence[str], None] = "e6d1c2e1e0fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("pricing_suggestion", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("marketing_copy", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "marketing_copy")
    op.drop_column("products", "pricing_suggestion")
