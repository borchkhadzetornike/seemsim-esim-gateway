"""Unit tests for error hierarchy."""

from __future__ import annotations

from app.core.errors import (
    AppError,
    IdempotencyConflictError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    ResourceNotFoundError,
)


class TestErrorHierarchy:
    def test_app_error_base(self) -> None:
        err = AppError("test error")
        assert err.detail == "test error"
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_ERROR"

    def test_provider_auth_error(self) -> None:
        err = ProviderAuthenticationError()
        assert err.status_code == 502
        assert err.error_code == "PROVIDER_AUTH_ERROR"

    def test_provider_rate_limit(self) -> None:
        err = ProviderRateLimitError()
        assert err.status_code == 429

    def test_provider_validation(self) -> None:
        err = ProviderValidationError("bad field")
        assert err.detail == "bad field"
        assert err.status_code == 422

    def test_provider_unavailable(self) -> None:
        err = ProviderUnavailableError()
        assert err.status_code == 503

    def test_provider_timeout(self) -> None:
        err = ProviderTimeoutError()
        assert err.status_code == 504

    def test_resource_not_found(self) -> None:
        err = ResourceNotFoundError(detail="Order xyz not found")
        assert err.status_code == 404
        assert "xyz" in err.detail

    def test_idempotency_conflict(self) -> None:
        err = IdempotencyConflictError()
        assert err.status_code == 409

    def test_to_dict(self) -> None:
        err = ProviderTimeoutError(detail="timed out")
        d = err.to_dict()
        assert d["error_code"] == "PROVIDER_TIMEOUT"
        assert d["detail"] == "timed out"
