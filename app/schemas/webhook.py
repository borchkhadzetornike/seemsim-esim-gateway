from __future__ import annotations

from typing import Any

from app.schemas.common import BaseSchema


class WebhookPayload(BaseSchema):
    """Raw webhook payload from eSIM Access.

    Fields are kept flexible since the provider may send various event types.
    """

    event_type: str | None = None
    order_no: str | None = None
    iccid: str | None = None
    transaction_id: str | None = None
    status: str | None = None
    raw: dict[str, Any] = {}


class WebhookResponse(BaseSchema):
    received: bool = True
    event_id: str | None = None
