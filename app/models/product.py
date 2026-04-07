from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import JSONBCompat


class ProviderProduct(Base):
    """A provider-sourced product grouping (e.g. a country or region)."""

    __tablename__ = "provider_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="esim_access")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    region_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    packages: Mapped[list[ProviderPackage]] = relationship(
        "ProviderPackage", back_populates="product", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_provider_products_provider", "provider_name"),
        Index("ix_provider_products_location", "location_code"),
        Index("ix_provider_products_type", "package_type"),
        Index("ix_provider_products_region", "region_code"),
    )


class ProviderPackage(Base):
    """A specific plan/package available from the provider."""

    __tablename__ = "provider_packages"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("provider_products.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="esim_access")
    package_code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="BASE")
    data_volume_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    countries: Mapped[list[str] | None] = mapped_column(JSONBCompat, nullable=True)
    support_topup_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    region_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_provider_data: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)

    product: Mapped[ProviderProduct] = relationship("ProviderProduct", back_populates="packages")

    __table_args__ = (
        Index("ix_provider_packages_product", "product_id"),
        Index("ix_provider_packages_code", "package_code"),
        Index("ix_provider_packages_type", "type"),
        Index("ix_provider_packages_pkg_type", "package_type"),
        Index("ix_provider_packages_region", "region_code"),
    )
