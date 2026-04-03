from __future__ import annotations

import uuid
from datetime import UTC, datetime


def generate_request_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


def ms_timestamp() -> str:
    return str(int(datetime.now(UTC).timestamp() * 1000))
