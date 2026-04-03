"""Add payload_hash column to provider_webhook_events for deduplication

Revision ID: 003
Revises: 002
Create Date: 2026-04-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("provider_webhook_events", "payload_hash"):
        op.add_column(
            "provider_webhook_events",
            sa.Column("payload_hash", sa.String(64), nullable=True),
        )
        op.create_index(
            "ix_webhook_events_payload_hash",
            "provider_webhook_events",
            ["payload_hash"],
        )


def downgrade() -> None:
    op.drop_index("ix_webhook_events_payload_hash", table_name="provider_webhook_events")
    if _column_exists("provider_webhook_events", "payload_hash"):
        op.drop_column("provider_webhook_events", "payload_hash")
