"""Unit tests for idempotency logic."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import IdempotencyConflictError, IdempotencyProcessingError
from app.core.idempotency import (
    IdempotencyManager,
    IdempotencyStatus,
    compute_request_fingerprint,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def manager(mock_redis: AsyncMock) -> IdempotencyManager:
    with patch("app.core.idempotency.get_settings") as mock_settings:
        mock_settings.return_value.idempotency_key_ttl_seconds = 3600
        return IdempotencyManager(redis=mock_redis)


class TestComputeFingerprint:
    def test_same_inputs_same_fingerprint(self) -> None:
        fp1 = compute_request_fingerprint("POST", "/v1/orders", b'{"a":1}')
        fp2 = compute_request_fingerprint("POST", "/v1/orders", b'{"a":1}')
        assert fp1 == fp2

    def test_different_method_different_fingerprint(self) -> None:
        fp1 = compute_request_fingerprint("POST", "/v1/orders", b"body")
        fp2 = compute_request_fingerprint("PUT", "/v1/orders", b"body")
        assert fp1 != fp2

    def test_different_path_different_fingerprint(self) -> None:
        fp1 = compute_request_fingerprint("POST", "/v1/orders", b"body")
        fp2 = compute_request_fingerprint("POST", "/v1/esims", b"body")
        assert fp1 != fp2

    def test_none_body(self) -> None:
        fp = compute_request_fingerprint("POST", "/test", None)
        assert isinstance(fp, str) and len(fp) == 64


class TestIdempotencyManager:
    @pytest.mark.asyncio
    async def test_check_or_lock_new_key_acquires_lock(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        result = await manager.check_or_lock("key-1", "fp-1")

        assert result is None
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_or_lock_completed_returns_record(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        stored = json.dumps(
            {
                "status": "completed",
                "status_code": 201,
                "response_body": '{"success":true}',
                "request_fingerprint": "fp-1",
            }
        )
        mock_redis.get.return_value = stored

        result = await manager.check_or_lock("key-1", "fp-1")

        assert result is not None
        assert result.status == IdempotencyStatus.COMPLETED
        assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_check_or_lock_processing_raises(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        stored = json.dumps(
            {
                "status": "processing",
                "request_fingerprint": "fp-1",
            }
        )
        mock_redis.get.return_value = stored

        with pytest.raises(IdempotencyProcessingError):
            await manager.check_or_lock("key-1", "fp-1")

    @pytest.mark.asyncio
    async def test_check_or_lock_fingerprint_mismatch_raises(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        stored = json.dumps(
            {
                "status": "completed",
                "status_code": 201,
                "response_body": "{}",
                "request_fingerprint": "different-fp",
            }
        )
        mock_redis.get.return_value = stored

        with pytest.raises(IdempotencyConflictError):
            await manager.check_or_lock("key-1", "fp-1")

    @pytest.mark.asyncio
    async def test_complete_stores_response(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        await manager.complete("key-1", 201, {"data": "test"}, "fp-1")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        stored = json.loads(call_args[0][1])
        assert stored["status"] == "completed"
        assert stored["status_code"] == 201

    @pytest.mark.asyncio
    async def test_release_deletes_key(
        self, manager: IdempotencyManager, mock_redis: AsyncMock
    ) -> None:
        await manager.release("key-1")
        mock_redis.delete.assert_called_once_with("idempotency:key-1")
