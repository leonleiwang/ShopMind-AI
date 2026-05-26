"""add contact center tables

Revision ID: f1b2c3d4e5f6
Revises: e8a1c6f4b902
Create Date: 2026-05-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f1b2c3d4e5f6"
down_revision = "e8a1c6f4b902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("support_tickets", sa.Column("ticket_id", sa.String(length=40), nullable=True))
    op.add_column("support_tickets", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.add_column(
        "support_tickets",
        sa.Column("conversation_id", sa.String(length=80), nullable=False, server_default=""),
    )
    op.add_column("support_tickets", sa.Column("channel", sa.String(length=40), nullable=False, server_default="web"))
    op.add_column(
        "support_tickets",
        sa.Column("assigned_agent", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column("support_tickets", sa.Column("summary", sa.Text(), nullable=False, server_default=""))
    op.add_column("support_tickets", sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"))
    op.add_column("support_tickets", sa.Column("handoff_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("support_tickets", sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE support_tickets SET ticket_id = 'TCK-' || id WHERE ticket_id IS NULL")
    op.execute("UPDATE support_tickets SET customer_id = user_id WHERE customer_id IS NULL")
    op.execute("UPDATE support_tickets SET summary = subject WHERE summary = ''")
    op.execute("UPDATE support_tickets SET status = 'pending' WHERE status = 'pending_review'")

    op.alter_column("support_tickets", "ticket_id", nullable=False)
    op.alter_column("support_tickets", "customer_id", nullable=False)
    op.create_foreign_key(
        "fk_support_tickets_customer_id_users",
        "support_tickets",
        "users",
        ["customer_id"],
        ["id"],
    )
    op.create_index(op.f("ix_support_tickets_ticket_id"), "support_tickets", ["ticket_id"], unique=True)
    op.create_index(op.f("ix_support_tickets_customer_id"), "support_tickets", ["customer_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_conversation_id"), "support_tickets", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_support_tickets_channel"), "support_tickets", ["channel"], unique=False)
    op.create_index(op.f("ix_support_tickets_assigned_agent"), "support_tickets", ["assigned_agent"], unique=False)
    op.create_index(op.f("ix_support_tickets_risk_level"), "support_tickets", ["risk_level"], unique=False)
    op.create_index(op.f("ix_support_tickets_sla_deadline"), "support_tickets", ["sla_deadline"], unique=False)
    op.create_index(op.f("ix_support_tickets_closed_at"), "support_tickets", ["closed_at"], unique=False)

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("to_status", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_events_id"), "ticket_events", ["id"], unique=False)
    op.create_index(op.f("ix_ticket_events_ticket_id"), "ticket_events", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ticket_events_actor_id"), "ticket_events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_ticket_events_event_type"), "ticket_events", ["event_type"], unique=False)

    op.create_table(
        "ticket_ai_assists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("intent", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("user_intent", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_reply", sa.Text(), nullable=False, server_default=""),
        sa.Column("knowledge_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("order_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("next_best_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("ai_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("routing_strategy", sa.String(length=40), nullable=False, server_default="rag"),
        sa.Column("llm_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("token_usage", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_ai_assists_id"), "ticket_ai_assists", ["id"], unique=False)
    op.create_index(op.f("ix_ticket_ai_assists_ticket_id"), "ticket_ai_assists", ["ticket_id"], unique=False)
    op.create_index(
        op.f("ix_ticket_ai_assists_conversation_id"),
        "ticket_ai_assists",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_ticket_ai_assists_intent"), "ticket_ai_assists", ["intent"], unique=False)
    op.create_index(op.f("ix_ticket_ai_assists_risk_level"), "ticket_ai_assists", ["risk_level"], unique=False)
    op.create_index(
        op.f("ix_ticket_ai_assists_routing_strategy"),
        "ticket_ai_assists",
        ["routing_strategy"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ticket_ai_assists_routing_strategy"), table_name="ticket_ai_assists")
    op.drop_index(op.f("ix_ticket_ai_assists_risk_level"), table_name="ticket_ai_assists")
    op.drop_index(op.f("ix_ticket_ai_assists_intent"), table_name="ticket_ai_assists")
    op.drop_index(op.f("ix_ticket_ai_assists_conversation_id"), table_name="ticket_ai_assists")
    op.drop_index(op.f("ix_ticket_ai_assists_ticket_id"), table_name="ticket_ai_assists")
    op.drop_index(op.f("ix_ticket_ai_assists_id"), table_name="ticket_ai_assists")
    op.drop_table("ticket_ai_assists")

    op.drop_index(op.f("ix_ticket_events_event_type"), table_name="ticket_events")
    op.drop_index(op.f("ix_ticket_events_actor_id"), table_name="ticket_events")
    op.drop_index(op.f("ix_ticket_events_ticket_id"), table_name="ticket_events")
    op.drop_index(op.f("ix_ticket_events_id"), table_name="ticket_events")
    op.drop_table("ticket_events")

    op.drop_index(op.f("ix_support_tickets_closed_at"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_sla_deadline"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_risk_level"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_assigned_agent"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_channel"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_conversation_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_customer_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_ticket_id"), table_name="support_tickets")
    op.drop_constraint("fk_support_tickets_customer_id_users", "support_tickets", type_="foreignkey")
    op.drop_column("support_tickets", "closed_at")
    op.drop_column("support_tickets", "sla_deadline")
    op.drop_column("support_tickets", "handoff_reason")
    op.drop_column("support_tickets", "risk_level")
    op.drop_column("support_tickets", "summary")
    op.drop_column("support_tickets", "assigned_agent")
    op.drop_column("support_tickets", "channel")
    op.drop_column("support_tickets", "conversation_id")
    op.drop_column("support_tickets", "customer_id")
    op.drop_column("support_tickets", "ticket_id")
