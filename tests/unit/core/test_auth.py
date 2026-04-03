"""Unit tests for eSIM Access HMAC authentication/signing.

Verified against live api.esimaccess.com calls on 2026-03-31.
Source of truth: docs.esimaccess.com + CONTRACT_REVALIDATION.md

  signData = timestamp + requestId + accessCode + body
  signature = HMAC-SHA256(secretKey, signData).hex().upper()
  Headers: RT-AccessCode, RT-RequestID, RT-Timestamp, RT-Signature
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from app.providers.esim_access.auth import EsimAccessAuth


@pytest.fixture
def auth() -> EsimAccessAuth:
    return EsimAccessAuth(access_code="test_access_code", secret_key="test_secret_key")


class TestSignatureConstruction:
    def test_sign_data_format(self, auth: EsimAccessAuth) -> None:
        """signData = timestamp + requestId + accessCode + body (no separators)."""
        sign_data = auth._build_sign_data("1700000000000", "req-id-123", '{"key":"val"}')
        assert sign_data == '1700000000000req-id-123test_access_code{"key":"val"}'

    def test_sign_data_no_separators(self, auth: EsimAccessAuth) -> None:
        sign_data = auth._build_sign_data("ts", "rid", "body")
        assert "&" not in sign_data

    def test_sign_data_includes_body(self, auth: EsimAccessAuth) -> None:
        data_with_body = auth._build_sign_data("ts", "rid", '{"foo":"bar"}')
        data_empty_body = auth._build_sign_data("ts", "rid", "{}")
        assert data_with_body != data_empty_body
        assert '{"foo":"bar"}' in data_with_body

    def test_sign_produces_valid_hmac_sha256(self, auth: EsimAccessAuth) -> None:
        timestamp = "1700000000000"
        request_id = "abc-123-def"
        body = '{"packageCode":"CKH511"}'

        signature = auth.sign(timestamp, request_id, body)

        expected_data = timestamp + request_id + "test_access_code" + body
        expected = hmac.new(
            b"test_secret_key", expected_data.encode(), hashlib.sha256
        ).hexdigest().upper()
        assert signature == expected

    def test_sign_output_is_uppercase_hex(self, auth: EsimAccessAuth) -> None:
        sig = auth.sign("123", "rid", "{}")
        assert sig == sig.upper()
        assert all(c in "0123456789ABCDEF" for c in sig)

    def test_sign_deterministic(self, auth: EsimAccessAuth) -> None:
        args = ("123", "rid", "{}")
        assert auth.sign(*args) == auth.sign(*args)

    def test_different_bodies_produce_different_signatures(self, auth: EsimAccessAuth) -> None:
        sig1 = auth.sign("123", "rid", '{"a":1}')
        sig2 = auth.sign("123", "rid", '{"b":2}')
        assert sig1 != sig2

    def test_different_timestamps_produce_different_signatures(self, auth: EsimAccessAuth) -> None:
        sig1 = auth.sign("100", "rid", "{}")
        sig2 = auth.sign("200", "rid", "{}")
        assert sig1 != sig2


class TestBuildHeaders:
    def test_contains_rt_header_names(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        assert "RT-AccessCode" in headers
        assert "RT-RequestID" in headers
        assert "RT-Timestamp" in headers
        assert "RT-Signature" in headers
        assert "Content-Type" in headers

    def test_does_not_contain_yoni_headers(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        assert "appId" not in headers
        assert "sign" not in headers

    def test_access_code_header_value(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        assert headers["RT-AccessCode"] == "test_access_code"

    def test_request_id_is_uuid_format(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        parts = headers["RT-RequestID"].split("-")
        assert len(parts) == 5

    def test_content_type_json(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        assert headers["Content-Type"] == "application/json"

    def test_signature_header_is_uppercase(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers("{}")
        sig = headers["RT-Signature"]
        assert sig == sig.upper()

    def test_signature_matches_sign_method(self, auth: EsimAccessAuth) -> None:
        headers = auth.build_headers('{"test":1}')
        ts = headers["RT-Timestamp"]
        rid = headers["RT-RequestID"]
        expected = auth.sign(ts, rid, '{"test":1}')
        assert headers["RT-Signature"] == expected


class TestTimestamp:
    def test_generate_timestamp_is_milliseconds(self, auth: EsimAccessAuth) -> None:
        ts = auth.generate_timestamp()
        assert len(ts) == 13
        assert ts.isdigit()
