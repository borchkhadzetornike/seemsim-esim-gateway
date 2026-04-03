"""Idempotency handling via Redis.

Workflow:
1. Client sends Idempotency-Key header on mutation requests.
2. We check Redis for an existing entry under that key.
   - If found and status=completed: return stored response immediately.
   - If found and status=processing: reject with 409 (concurrent retry).
   - If not found: set status=processing with a TTL and proceed.
3. After the request completes, store the response and mark status=completed.
4. If the request fails, remove the key so it can be retried.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings
from app.core.errors import IdempotencyConflictError, IdempotencyProcessingError

logger = structlog.get_logger(__name__)


class IdempotencyStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    status: IdempotencyStatus
    status_code: int | None = None
    response_body: str | None = None
    request_fingerprint: str | None = None


def compute_request_fingerprint(method: str, path: str, body: bytes | None) -> str:
    h = hashlib.sha256()
    h.update(method.encode())
    h.update(path.encode())
    if body:
        h.update(body)
    return h.hexdigest()


class IdempotencyManager:
    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis
        self._ttl = get_settings().idempotency_key_ttl_seconds

    async def check_or_lock(self, key: str, request_fingerprint: str) -> IdempotencyRecord | None:
        """Check for existing idempotency record. Lock if new.

        Returns the existing record if found and completed, None if we acquired the lock.
        Raises IdempotencyProcessingError if another request is processing.
        Raises IdempotencyConflictError if fingerprint doesn't match.
        """
        existing_raw = await self._redis.get(f"idempotency:{key}")

        if existing_raw is not None:
            existing = json.loads(existing_raw)
            record = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus(existing["status"]),
                status_code=existing.get("status_code"),
                response_body=existing.get("response_body"),
                request_fingerprint=existing.get("request_fingerprint"),
            )

            if record.request_fingerprint and record.request_fingerprint != request_fingerprint:
                raise IdempotencyConflictError(
                    detail="Idempotency key already used with a different request"
                )

            if record.status == IdempotencyStatus.PROCESSING:
                raise IdempotencyProcessingError()

            return record

        payload = json.dumps(
            {
                "status": IdempotencyStatus.PROCESSING,
                "request_fingerprint": request_fingerprint,
            }
        )
        acquired = await self._redis.set(
            f"idempotency:{key}",
            payload,
            nx=True,
            ex=self._ttl,
        )

        if not acquired:
            raise IdempotencyProcessingError()

        return None

    async def complete(
        self,
        key: str,
        status_code: int,
        response_body: Any,
        request_fingerprint: str,
    ) -> None:
        payload = json.dumps(
            {
                "status": IdempotencyStatus.COMPLETED,
                "status_code": status_code,
                "response_body": (
                    json.dumps(response_body)
                    if not isinstance(response_body, str)
                    else response_body
                ),
                "request_fingerprint": request_fingerprint,
            }
        )
        await self._redis.set(f"idempotency:{key}", payload, ex=self._ttl)
        logger.info("idempotency_completed", key=key)

    async def release(self, key: str) -> None:
        await self._redis.delete(f"idempotency:{key}")
        logger.info("idempotency_released", key=key)
