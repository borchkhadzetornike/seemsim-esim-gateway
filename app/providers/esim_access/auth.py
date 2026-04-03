"""eSIM Access HMAC-SHA256 authentication and request signing.

Verified by live API calls against api.esimaccess.com on 2026-03-31.
Source of truth: docs.esimaccess.com + CONTRACT_REVALIDATION.md

Headers required on every request:
  RT-AccessCode  — AccessCode from console.esimaccess.com
  RT-RequestID   — Unique UUID per request
  RT-Timestamp   — Current timestamp in milliseconds
  RT-Signature   — HMAC-SHA256 signature, UPPERCASE hex

Signature algorithm:
  signData = timestamp + requestId + accessCode + body
  signature = HMAC-SHA256(secretKey, signData).hex().upper()
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid


class EsimAccessAuth:
    def __init__(self, access_code: str, secret_key: str) -> None:
        self._access_code = access_code
        self._secret_key = secret_key

    @property
    def access_code(self) -> str:
        return self._access_code

    def generate_timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def generate_request_id(self) -> str:
        return str(uuid.uuid4())

    def sign(self, timestamp: str, request_id: str, body: str) -> str:
        """Produce HMAC-SHA256 uppercase hex signature."""
        sign_data = self._build_sign_data(timestamp, request_id, body)
        return hmac.new(
            self._secret_key.encode("utf-8"),
            sign_data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

    def build_headers(self, body: str) -> dict[str, str]:
        timestamp = self.generate_timestamp()
        request_id = self.generate_request_id()
        signature = self.sign(timestamp, request_id, body)

        return {
            "RT-AccessCode": self._access_code,
            "RT-RequestID": request_id,
            "RT-Timestamp": timestamp,
            "RT-Signature": signature,
            "Content-Type": "application/json",
        }

    def _build_sign_data(self, timestamp: str, request_id: str, body: str) -> str:
        return timestamp + request_id + self._access_code + body
