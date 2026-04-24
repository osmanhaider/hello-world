"""Simple shared-password auth for demo deployments.

Tokens are HMAC-SHA256 signed payloads (`base64url(json).hex-sig`). No
database, no user model, no JWT dependency — just enough to keep a
public Render URL from being scraped by anyone with the link.

Environment:
    APP_PASSWORD   Shared password. Required for auth to be active.
    AUTH_SECRET    HMAC signing secret. Required when APP_PASSWORD is set.
    TOKEN_TTL_SEC  Optional. Token lifetime in seconds (default 7 days).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


class AuthError(Exception):
    pass


APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
AUTH_SECRET = os.environ.get("AUTH_SECRET", "")
TOKEN_TTL_SEC = int(os.environ.get("TOKEN_TTL_SEC", 7 * 24 * 3600))


def auth_enabled() -> bool:
    return bool(APP_PASSWORD)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(ttl_sec: int | None = None) -> str:
    if not AUTH_SECRET:
        raise AuthError("AUTH_SECRET is not configured")
    payload = {"exp": int(time.time()) + (ttl_sec or TOKEN_TTL_SEC)}
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> dict:
    if not AUTH_SECRET:
        raise AuthError("AUTH_SECRET is not configured")
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError as e:
        raise AuthError("malformed token") from e
    expected = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise AuthError("invalid signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError) as e:
        raise AuthError("invalid payload") from e
    if int(payload.get("exp", 0)) < int(time.time()):
        raise AuthError("token expired")
    return payload


def verify_password(candidate: str) -> bool:
    if not APP_PASSWORD:
        return False
    return hmac.compare_digest(candidate.encode(), APP_PASSWORD.encode())
