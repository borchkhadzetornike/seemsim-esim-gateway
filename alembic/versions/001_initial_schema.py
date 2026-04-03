"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_products",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_code", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_products_provider", "provider_products", ["provider_name"])
    op.create_index("ix_provider_products_location", "provider_products", ["location_code"])

    op.create_table(
        "provider_packages",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("product_id", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("package_code", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="BASE"),
        sa.Column("data_volume_mb", sa.Integer(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("countries", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("raw_provider_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_packages_product", "provider_packages", ["product_id"])
    op.create_index("ix_provider_packages_code", "provider_packages", ["package_code"])
    op.create_index("ix_provider_packages_type", "provider_packages", ["type"])

    op.create_table(
        "provider_orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("provider_order_no", sa.String(128), nullable=True),
        sa.Column("transaction_id", sa.String(128), nullable=False, unique=True),
        sa.Column("package_code", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("iccid", sa.String(64), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("raw_provider_request", postgresql.JSONB(), nullable=True),
        sa.Column("raw_provider_response", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_orders_provider_order", "provider_orders", ["provider_order_no"])
    op.create_index("ix_provider_orders_transaction", "provider_orders", ["transaction_id"])
    op.create_index("ix_provider_orders_status", "provider_orders", ["status"])
    op.create_index("ix_provider_orders_iccid", "provider_orders", ["iccid"])

    op.create_table(
        "esims",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("iccid", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("smdp_address", sa.String(512), nullable=True),
        sa.Column("matching_id", sa.String(512), nullable=True),
        sa.Column("activation_code", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="allocated"),
        sa.Column("msisdn", sa.String(32), nullable=True),
        sa.Column("raw_provider_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_esims_iccid", "esims", ["iccid"])
    op.create_index("ix_esims_order", "esims", ["order_id"])
    op.create_index("ix_esims_status", "esims", ["status"])

    op.create_table(
        "esim_status_history",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("esim_id", sa.String(64), nullable=False),
        sa.Column("iccid", sa.String(64), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="api"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_esim_status_history_esim", "esim_status_history", ["esim_id"])
    op.create_index("ix_esim_status_history_iccid", "esim_status_history", ["iccid"])

    op.create_table(
        "provider_webhook_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("order_no", sa.String(128), nullable=True),
        sa.Column("iccid", sa.String(64), nullable=True),
        sa.Column("transaction_id", sa.String(128), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_events_type", "provider_webhook_events", ["event_type"])
    op.create_index("ix_webhook_events_order", "provider_webhook_events", ["order_no"])
    op.create_index("ix_webhook_events_processed", "provider_webhook_events", ["processed"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.String(128), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_idempotency_key", "idempotency_records", ["idempotency_key"])

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="esim_access"),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_operation_logs_operation", "operation_logs", ["operation"])
    op.create_index("ix_operation_logs_status", "operation_logs", ["status"])
    op.create_index("ix_operation_logs_request_id", "operation_logs", ["request_id"])


def downgrade() -> None:
    op.drop_table("operation_logs")
    op.drop_table("idempotency_records")
    op.drop_table("provider_webhook_events")
    op.drop_table("esim_status_history")
    op.drop_table("esims")
    op.drop_table("provider_orders")
    op.drop_table("provider_packages")
    op.drop_table("provider_products")
