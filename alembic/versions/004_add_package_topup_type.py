"""Add support_topup_type column to provider_packages

Revision ID: 004
Revises: 003
Create Date: 2026-04-06
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("provider_packages", "support_topup_type"):
        op.add_column(
            "provider_packages",
            sa.Column("support_topup_type", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("provider_packages", "support_topup_type"):
        op.drop_column("provider_packages", "support_topup_type")
