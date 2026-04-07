"""Add package_type and region_code to provider_products and provider_packages

Revision ID: 005
Revises: 004
Create Date: 2026-04-07
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    # -- provider_products --
    if not _column_exists("provider_products", "package_type"):
        op.add_column(
            "provider_products",
            sa.Column("package_type", sa.String(20), server_default="local", nullable=False),
        )
    if not _column_exists("provider_products", "region_code"):
        op.add_column(
            "provider_products",
            sa.Column("region_code", sa.String(50), nullable=True),
        )
    op.create_index("ix_provider_products_type", "provider_products", ["package_type"], unique=False)
    op.create_index("ix_provider_products_region", "provider_products", ["region_code"], unique=False)

    # -- provider_packages --
    if not _column_exists("provider_packages", "package_type"):
        op.add_column(
            "provider_packages",
            sa.Column("package_type", sa.String(20), server_default="local", nullable=False),
        )
    if not _column_exists("provider_packages", "region_code"):
        op.add_column(
            "provider_packages",
            sa.Column("region_code", sa.String(50), nullable=True),
        )
    op.create_index("ix_provider_packages_pkg_type", "provider_packages", ["package_type"], unique=False)
    op.create_index("ix_provider_packages_region", "provider_packages", ["region_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_provider_packages_region", table_name="provider_packages")
    op.drop_index("ix_provider_packages_pkg_type", table_name="provider_packages")
    if _column_exists("provider_packages", "region_code"):
        op.drop_column("provider_packages", "region_code")
    if _column_exists("provider_packages", "package_type"):
        op.drop_column("provider_packages", "package_type")

    op.drop_index("ix_provider_products_region", table_name="provider_products")
    op.drop_index("ix_provider_products_type", table_name="provider_products")
    if _column_exists("provider_products", "region_code"):
        op.drop_column("provider_products", "region_code")
    if _column_exists("provider_products", "package_type"):
        op.drop_column("provider_products", "package_type")
