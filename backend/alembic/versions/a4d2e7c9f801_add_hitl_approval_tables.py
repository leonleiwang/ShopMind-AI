"""add hitl approval tables

Revision ID: a4d2e7c9f801
Revises: c9b8a72e4f31
Create Date: 2026-05-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a4d2e7c9f801"
down_revision = "c9b8a72e4f31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("risk_reasons", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_requests_id"), "approval_requests", ["id"], unique=False)
    op.create_index(op.f("ix_approval_requests_user_id"), "approval_requests", ["user_id"], unique=False)
    op.create_index(op.f("ix_approval_requests_action_type"), "approval_requests", ["action_type"], unique=False)
    op.create_index(op.f("ix_approval_requests_status"), "approval_requests", ["status"], unique=False)

    op.create_table(
        "approval_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("approval_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_audit_logs_id"), "approval_audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_approval_audit_logs_approval_id"), "approval_audit_logs", ["approval_id"], unique=False)
    op.create_index(op.f("ix_approval_audit_logs_user_id"), "approval_audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_approval_audit_logs_event"), "approval_audit_logs", ["event"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_approval_audit_logs_event"), table_name="approval_audit_logs")
    op.drop_index(op.f("ix_approval_audit_logs_user_id"), table_name="approval_audit_logs")
    op.drop_index(op.f("ix_approval_audit_logs_approval_id"), table_name="approval_audit_logs")
    op.drop_index(op.f("ix_approval_audit_logs_id"), table_name="approval_audit_logs")
    op.drop_table("approval_audit_logs")
    op.drop_index(op.f("ix_approval_requests_status"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_action_type"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_user_id"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_id"), table_name="approval_requests")
    op.drop_table("approval_requests")
