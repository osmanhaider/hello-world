"""Unit tests for the app session token module."""
from __future__ import annotations

import importlib
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(__file__))


def _reload_auth(monkeypatch, *, secret: str = "x" * 64, ttl: int | None = None):
    if secret:
        monkeypatch.setenv("AUTH_SECRET", secret)
    else:
        monkeypatch.delenv("AUTH_SECRET", raising=False)
    if ttl is not None:
        monkeypatch.setenv("TOKEN_TTL_SEC", str(ttl))
    else:
        monkeypatch.delenv("TOKEN_TTL_SEC", raising=False)
    import auth
    return importlib.reload(auth)


def test_token_roundtrip_carries_identity(monkeypatch):
    auth = _reload_auth(monkeypatch)
    tok = auth.create_token(
        sub="google-sub-123",
        email="alice@example.com",
        name="Alice",
        picture="https://example.com/a.png",
    )
    payload = auth.verify_token(tok)
    assert payload["exp"] > int(time.time())
    assert payload["sub"] == "google-sub-123"
    assert payload["email"] == "alice@example.com"
    assert payload["name"] == "Alice"
    assert payload["picture"] == "https://example.com/a.png"


def test_token_carries_distinct_user_ids(monkeypatch):
    auth = _reload_auth(monkeypatch)
    tok_a = auth.create_token(sub="alice", email="a@x.com")
    tok_b = auth.create_token(sub="bob", email="b@x.com")
    assert auth.verify_token(tok_a)["sub"] == "alice"
    assert auth.verify_token(tok_b)["sub"] == "bob"
    assert tok_a != tok_b


def test_token_tampered_signature_rejected(monkeypatch):
    auth = _reload_auth(monkeypatch)
    tok = auth.create_token(sub="alice", email="a@x.com")
    body, sig = tok.rsplit(".", 1)
    tampered = f"{body}.{'0' * len(sig)}"
    with pytest.raises(auth.AuthError):
        auth.verify_token(tampered)


def test_token_tampered_payload_rejected(monkeypatch):
    auth = _reload_auth(monkeypatch)
    tok = auth.create_token(sub="alice", email="a@x.com")
    body, sig = tok.rsplit(".", 1)
    flipped_char = "A" if body[-1] != "A" else "B"
    tampered = body[:-1] + flipped_char + "." + sig
    with pytest.raises(auth.AuthError):
        auth.verify_token(tampered)


def test_token_expired(monkeypatch):
    auth = _reload_auth(monkeypatch)
    tok = auth.create_token(sub="alice", email="a@x.com", ttl_sec=-1)
    with pytest.raises(auth.AuthError, match="expired"):
        auth.verify_token(tok)


def test_token_malformed(monkeypatch):
    auth = _reload_auth(monkeypatch)
    with pytest.raises(auth.AuthError):
        auth.verify_token("not-a-real-token")


def test_secret_required_for_create(monkeypatch):
    auth = _reload_auth(monkeypatch, secret="")
    with pytest.raises(auth.AuthError):
        auth.create_token(sub="alice", email="a@x.com")


def test_different_secrets_produce_incompatible_tokens(monkeypatch):
    auth_a = _reload_auth(monkeypatch, secret="secret-a" * 8)
    tok = auth_a.create_token(sub="alice", email="a@x.com")
    auth_b = _reload_auth(monkeypatch, secret="secret-b" * 8)
    with pytest.raises(auth_b.AuthError):
        auth_b.verify_token(tok)


def test_token_missing_sub_rejected(monkeypatch):
    """A correctly signed token whose payload has no `sub` claim is invalid."""
    auth = _reload_auth(monkeypatch)
    # Build a hand-rolled token with an empty sub to confirm verify_token rejects it.
    import json as _json
    bad_payload = auth._b64url_encode(
        _json.dumps({"sub": "", "exp": int(time.time()) + 60}).encode()
    )
    import hashlib as _hashlib
    import hmac as _hmac
    sig = _hmac.new(
        auth.AUTH_SECRET.encode(), bad_payload.encode(), _hashlib.sha256
    ).hexdigest()
    tok = f"{bad_payload}.{sig}"
    with pytest.raises(auth.AuthError, match="sub"):
        auth.verify_token(tok)
