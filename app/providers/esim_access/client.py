"""Low-level HTTP client for eSIM Access API.

Verified endpoint base: https://api.esimaccess.com
All endpoints under /api/v1/open/...
All endpoints use POST with JSON bodies.
Response envelope: {success, errorCode, errorMsg, obj}

Source of truth: docs.esimaccess.com + CONTRACT_REVALIDATION.md
"""

from __future__ import annotations

import json as json_lib
import time
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.errors import (
    ProviderAuthenticationError,
    ProviderProcessingError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.providers.esim_access.auth import EsimAccessAuth

logger = structlog.get_logger(__name__)


class EsimAccessClient:
    """Async HTTP client for eSIM Access API with signing and retry."""

    def __init__(
        self,
        auth: EsimAccessAuth,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._auth = auth
        self._base_url = (base_url or "https://api.esimaccess.com").rstrip("/")
        self._timeout = httpx.Timeout(timeout=timeout_seconds, connect=10.0)
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed POST request to the provider.

        Args:
            path: URL path starting with /api/v1/open/...
            payload: JSON body dict (may be empty).
        """
        return await self._request_with_retry(path, payload or {})

    @retry(
        retry=retry_if_exception_type((ProviderProcessingError, ProviderUnavailableError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=2),
        reraise=True,
    )
    async def _request_with_retry(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path

        body_str = json_lib.dumps(payload, separators=(",", ":"))
        headers = self._auth.build_headers(body_str)

        client = await self._get_client()
        start = time.perf_counter()

        try:
            logger.info("provider_request_start", path=path)

            response = await client.post(path, content=body_str, headers=headers)

            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "provider_request_complete",
                path=path,
                status_code=response.status_code,
                elapsed_ms=elapsed_ms,
            )

            if response.status_code == 401:
                raise ProviderAuthenticationError(
                    detail="Provider returned HTTP 401 — check AccessCode/secretKey"
                )

            if response.status_code == 429:
                raise ProviderRateLimitError()

            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    detail=f"Provider returned HTTP {response.status_code}"
                )

            data: dict[str, Any] = response.json()
            return self._handle_response(data, path)

        except httpx.TimeoutException as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("provider_request_timeout", path=path, elapsed_ms=elapsed_ms)
            raise ProviderTimeoutError(
                detail=f"Request to {path} timed out after {elapsed_ms}ms"
            ) from exc
        except httpx.HTTPError as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("provider_request_error", path=path, elapsed_ms=elapsed_ms, error=str(exc))
            raise ProviderUnavailableError(
                detail=f"HTTP error communicating with provider: {exc}"
            ) from exc

    def _handle_response(self, data: dict[str, Any], path: str) -> dict[str, Any]:
        """Parse the eSIM Access response envelope: {success, errorCode, errorMsg, obj}."""
        success = data.get("success", False)
        error_code = str(data.get("errorCode") or "")
        error_msg = str(data.get("errorMsg") or "")

        if success is True or error_code == "0":
            return data

        if error_code in ("000101", "000102", "000103"):
            raise ProviderAuthenticationError(detail=f"[{error_code}] {error_msg}")

        if error_code.startswith("000105"):
            raise ProviderValidationError(detail=f"[{error_code}] {error_msg}")

        if error_code == "404":
            raise ProviderValidationError(detail=f"[{error_code}] {error_msg}")

        if error_code.startswith("3"):
            raise ProviderValidationError(detail=f"[{error_code}] {error_msg}")

        logger.warning(
            "provider_response_unhandled_code",
            path=path,
            error_code=error_code,
            error_msg=error_msg,
        )
        raise ProviderUnavailableError(detail=f"[{error_code}] {error_msg}")
