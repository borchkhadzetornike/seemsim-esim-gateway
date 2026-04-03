"""State synchronization schema additions

Revision ID: 002
Revises: 001
Create Date: 2026-03-31

Adds columns for provider state tracking, eSIM detail fields,
webhook processing metadata, and order state history table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- provider_orders: state sync columns ---
    op.add_column(
        "provider_orders",
        sa.Column("provider_status", sa.String(100), nullable=True),
    )
    op.add_column(
        "provider_orders",
        sa.Column("last_provider_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "provider_orders",
        sa.Column("last_provider_payload", postgresql.JSONB(), nullable=True),
    )

    # --- esims: rich provider detail columns ---
    op.add_column("esims", sa.Column("provider_esim_tran_no", sa.String(128), nullable=True))
    op.add_column("esims", sa.Column("imsi", sa.String(64), nullable=True))
    op.add_column("esims", sa.Column("qr_code_url", sa.Text(), nullable=True))
    op.add_column("esims", sa.Column("short_url", sa.Text(), nullable=True))
    op.add_column("esims", sa.Column("smdp_status", sa.String(50), nullable=True))
    op.add_column("esims", sa.Column("esim_status", sa.String(50), nullable=True))
    op.add_column("esims", sa.Column("pin", sa.String(32), nullable=True))
    op.add_column("esims", sa.Column("puk", sa.String(32), nullable=True))
    op.add_column("esims", sa.Column("apn", sa.String(128), nullable=True))
    op.add_column("esims", sa.Column("total_volume", sa.BigInteger(), nullable=True))
    op.add_column("esims", sa.Column("total_duration", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("duration_unit", sa.String(20), nullable=True))
    op.add_column("esims", sa.Column("order_usage", sa.BigInteger(), nullable=True))
    op.add_column(
        "esims",
        sa.Column("activate_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "esims",
        sa.Column("installation_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "esims",
        sa.Column("expired_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("esims", sa.Column("support_topup_type", sa.Integer(), nullable=True))
    op.add_column("esims", sa.Column("fup_policy", sa.String(255), nullable=True))
    op.add_column(
        "esims",
        sa.Column("raw_provider_payload", postgresql.JSONB(), nullable=True),
    )

    # --- provider_webhook_events: processing metadata ---
    op.add_column(
        "provider_webhook_events",
        sa.Column("provider_event_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "provider_webhook_events",
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "provider_webhook_events",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "provider_webhook_events",
        sa.Column(
            "processing_status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_webhook_events_processing_status",
        "provider_webhook_events",
        ["processing_status"],
    )

    # --- order_state_history: new table ---
    op.create_table(
        "order_state_history",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("old_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=True),
        sa.Column("old_provider_status", sa.String(100), nullable=True),
        sa.Column("new_provider_status", sa.String(100), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_order_state_history_order", "order_state_history", ["order_id"])
    op.create_index("ix_order_state_history_source", "order_state_history", ["source"])

    # --- fix location_code width from migration 001 (already ALTERed in prod) ---
    op.alter_column(
        "provider_products",
        "location_code",
        type_=sa.String(255),
        existing_type=sa.String(10),
    )


def downgrade() -> None:
    op.alter_column(
        "provider_products",
        "location_code",
        type_=sa.String(10),
        existing_type=sa.String(255),
    )

    op.drop_index("ix_order_state_history_source", table_name="order_state_history")
    op.drop_index("ix_order_state_history_order", table_name="order_state_history")
    op.drop_table("order_state_history")

    op.drop_index(
        "ix_webhook_events_processing_status", table_name="provider_webhook_events"
    )
    op.drop_column("provider_webhook_events", "processing_status")
    op.drop_column("provider_webhook_events", "processed_at")
    op.drop_column("provider_webhook_events", "received_at")
    op.drop_column("provider_webhook_events", "provider_event_id")

    op.drop_column("esims", "raw_provider_payload")
    op.drop_column("esims", "fup_policy")
    op.drop_column("esims", "support_topup_type")
    op.drop_column("esims", "expired_time")
    op.drop_column("esims", "installation_time")
    op.drop_column("esims", "activate_time")
    op.drop_column("esims", "order_usage")
    op.drop_column("esims", "duration_unit")
    op.drop_column("esims", "total_duration")
    op.drop_column("esims", "total_volume")
    op.drop_column("esims", "apn")
    op.drop_column("esims", "puk")
    op.drop_column("esims", "pin")
    op.drop_column("esims", "esim_status")
    op.drop_column("esims", "smdp_status")
    op.drop_column("esims", "short_url")
    op.drop_column("esims", "qr_code_url")
    op.drop_column("esims", "imsi")
    op.drop_column("esims", "provider_esim_tran_no")

    op.drop_column("provider_orders", "last_provider_payload")
    op.drop_column("provider_orders", "last_provider_sync_at")
    op.drop_column("provider_orders", "provider_status")
