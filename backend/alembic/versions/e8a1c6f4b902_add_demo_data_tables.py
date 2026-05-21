"""add demo data support tables

Revision ID: e8a1c6f4b902
Revises: d5c7b12a9e44
Create Date: 2026-05-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e8a1c6f4b902"
down_revision = "d5c7b12a9e44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preferred_categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_brands", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("disliked_tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("shipping_city", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f("ix_user_preferences_id"), "user_preferences", ["id"], unique=False)
    op.create_index(op.f("ix_user_preferences_user_id"), "user_preferences", ["user_id"], unique=True)

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_support_tickets_id"), "support_tickets", ["id"], unique=False)
    op.create_index(op.f("ix_support_tickets_user_id"), "support_tickets", ["user_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_order_id"), "support_tickets", ["order_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_category"), "support_tickets", ["category"], unique=False)
    op.create_index(op.f("ix_support_tickets_status"), "support_tickets", ["status"], unique=False)
    op.create_index(op.f("ix_support_tickets_priority"), "support_tickets", ["priority"], unique=False)

    op.create_table(
        "agent_execution_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("conversation_id", sa.String(length=80), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=40), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tool_calls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("failure_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f("ix_agent_execution_logs_id"), "agent_execution_logs", ["id"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_user_id"), "agent_execution_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_conversation_id"), "agent_execution_logs", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_intent"), "agent_execution_logs", ["intent"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_status"), "agent_execution_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_execution_logs_status"), table_name="agent_execution_logs")
    op.drop_index(op.f("ix_agent_execution_logs_intent"), table_name="agent_execution_logs")
    op.drop_index(op.f("ix_agent_execution_logs_conversation_id"), table_name="agent_execution_logs")
    op.drop_index(op.f("ix_agent_execution_logs_user_id"), table_name="agent_execution_logs")
    op.drop_index(op.f("ix_agent_execution_logs_id"), table_name="agent_execution_logs")
    op.drop_table("agent_execution_logs")

    op.drop_index(op.f("ix_support_tickets_priority"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_status"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_category"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_order_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_id"), table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index(op.f("ix_user_preferences_user_id"), table_name="user_preferences")
    op.drop_index(op.f("ix_user_preferences_id"), table_name="user_preferences")
    op.drop_table("user_preferences")
