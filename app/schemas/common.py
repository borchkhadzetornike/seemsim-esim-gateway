from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ApiResponse(BaseSchema, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None


class ErrorDetail(BaseSchema):
    error_code: str
    detail: str


class PaginatedResponse(BaseSchema, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseSchema):
    status: str
    service: str
    timestamp: datetime
    checks: dict[str, Any] | None = None
