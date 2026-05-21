"""add product structured metadata

Revision ID: d5c7b12a9e44
Revises: b8f3a6d41c2e
Create Date: 2026-05-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d5c7b12a9e44"
down_revision = "b8f3a6d41c2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    op.add_column("products", sa.Column("attributes", sa.JSON(), nullable=True))
    op.add_column("products", sa.Column("tags", sa.JSON(), nullable=True))

    conn.exec_driver_sql("UPDATE products SET attributes = '{}', tags = '[]' WHERE attributes IS NULL")
    conn.exec_driver_sql(
        """
        UPDATE products
        SET attributes = '{"latency":"medium","sound_quality":"medium","use_cases":["daily","commute"],"noise_cancellation":false,"bluetooth_version":"5.2"}',
            tags = '["budget","medium_latency","daily_use","commute"]'
        WHERE name ILIKE '%蓝牙耳机%lite%'
        """
    )
    conn.exec_driver_sql(
        """
        UPDATE products
        SET attributes = '{"latency":"low","sound_quality":"high","use_cases":["gaming","commute"],"noise_cancellation":true,"bluetooth_version":"5.3"}',
            tags = '["pro","low_latency","gaming","noise_cancellation"]'
        WHERE name ILIKE '%蓝牙耳机%pro%'
        """
    )
    conn.exec_driver_sql(
        """
        UPDATE products
        SET attributes = '{"latency":"medium","sound_quality":"medium","use_cases":["daily"],"noise_cancellation":false,"bluetooth_version":"5.2"}',
            tags = '["medium_latency","daily_use"]'
        WHERE name ILIKE '%蓝牙耳机%'
          AND name NOT ILIKE '%pro%'
          AND name NOT ILIKE '%lite%'
        """
    )

    op.alter_column("products", "attributes", nullable=False)
    op.alter_column("products", "tags", nullable=False)


def downgrade() -> None:
    op.drop_column("products", "tags")
    op.drop_column("products", "attributes")
