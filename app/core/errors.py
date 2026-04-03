from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error."""

    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None, **context: Any) -> None:
        self.detail = detail or self.__class__.detail
        self.context = context
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "detail": self.detail,
        }


# --- Provider errors ---


class ProviderError(AppError):
    error_code = "PROVIDER_ERROR"
    status_code = 502
    detail = "Provider communication error"


class ProviderAuthenticationError(ProviderError):
    error_code = "PROVIDER_AUTH_ERROR"
    status_code = 502
    detail = "Provider authentication failed"


class ProviderRateLimitError(ProviderError):
    error_code = "PROVIDER_RATE_LIMIT"
    status_code = 429
    detail = "Provider rate limit exceeded"


class ProviderValidationError(ProviderError):
    error_code = "PROVIDER_VALIDATION_ERROR"
    status_code = 422
    detail = "Provider rejected request as invalid"


class ProviderUnavailableError(ProviderError):
    error_code = "PROVIDER_UNAVAILABLE"
    status_code = 503
    detail = "Provider service is unavailable"


class ProviderTimeoutError(ProviderError):
    error_code = "PROVIDER_TIMEOUT"
    status_code = 504
    detail = "Provider request timed out"


class ProviderProcessingError(ProviderError):
    """Provider returned 101 (processing) - should be retried."""

    error_code = "PROVIDER_PROCESSING"
    status_code = 202
    detail = "Provider is still processing the request"


# --- Application errors ---


class ResourceNotFoundError(AppError):
    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    detail = "Resource not found"


class IntegrationConflictError(AppError):
    error_code = "INTEGRATION_CONFLICT"
    status_code = 409
    detail = "Integration conflict"


class IdempotencyConflictError(AppError):
    error_code = "IDEMPOTENCY_CONFLICT"
    status_code = 409
    detail = "Idempotency key conflict: same key used with different request"


class IdempotencyProcessingError(AppError):
    error_code = "IDEMPOTENCY_PROCESSING"
    status_code = 409
    detail = "Request with this idempotency key is currently being processed"


class ValidationError(AppError):
    error_code = "VALIDATION_ERROR"
    status_code = 422
    detail = "Request validation failed"


class AuthenticationError(AppError):
    error_code = "AUTHENTICATION_ERROR"
    status_code = 401
    detail = "Authentication required"


class AuthorizationError(AppError):
    error_code = "AUTHORIZATION_ERROR"
    status_code = 403
    detail = "Insufficient permissions"


class ProviderCapabilityUnavailableError(ProviderError):
    error_code = "PROVIDER_CAPABILITY_UNAVAILABLE"
    status_code = 501
    detail = "This capability is not supported by the current provider"
