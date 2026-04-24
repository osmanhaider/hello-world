"""Unit tests for the shared-password auth module."""
from __future__ import annotations

import importlib
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(__file__))


def _reload_auth(monkeypatch, *, password: str = "", secret: str = "", ttl: int | None = None):
    if password:
        monkeypatch.setenv("APP_PASSWORD", password)
    else:
        monkeypatch.delenv("APP_PASSWORD", raising=False)
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


def test_auth_disabled_when_password_unset(monkeypatch):
    auth = _reload_auth(monkeypatch)
    assert auth.auth_enabled() is False


def test_auth_enabled_when_password_set(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    assert auth.auth_enabled() is True


def test_verify_password_constant_time(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    assert auth.verify_password("hunter2") is True
    assert auth.verify_password("wrong") is False
    assert auth.verify_password("") is False


def test_token_roundtrip(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    tok = auth.create_token("user-abc")
    payload = auth.verify_token(tok)
    assert payload["exp"] > int(time.time())
    assert payload["sub"] == "user-abc"


def test_token_carries_distinct_user_ids(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    tok_a = auth.create_token("alice")
    tok_b = auth.create_token("bob")
    assert auth.verify_token(tok_a)["sub"] == "alice"
    assert auth.verify_token(tok_b)["sub"] == "bob"
    assert tok_a != tok_b


def test_token_tampered_signature_rejected(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    tok = auth.create_token("user-abc")
    body, sig = tok.rsplit(".", 1)
    tampered = f"{body}.{'0' * len(sig)}"
    with pytest.raises(auth.AuthError):
        auth.verify_token(tampered)


def test_token_tampered_payload_rejected(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    tok = auth.create_token("user-abc")
    body, sig = tok.rsplit(".", 1)
    # Flip the last character of the payload — signature should no longer match.
    flipped_char = "A" if body[-1] != "A" else "B"
    tampered = body[:-1] + flipped_char + "." + sig
    with pytest.raises(auth.AuthError):
        auth.verify_token(tampered)


def test_token_expired(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    tok = auth.create_token("user-abc", ttl_sec=-1)
    with pytest.raises(auth.AuthError, match="expired"):
        auth.verify_token(tok)


def test_token_malformed(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="x" * 64)
    with pytest.raises(auth.AuthError):
        auth.verify_token("not-a-real-token")


def test_secret_required_for_create(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2")  # no secret
    with pytest.raises(auth.AuthError):
        auth.create_token("user-abc")


def test_different_secrets_produce_incompatible_tokens(monkeypatch):
    auth = _reload_auth(monkeypatch, password="hunter2", secret="secret-a" * 8)
    tok = auth.create_token("user-abc")
    auth2 = _reload_auth(monkeypatch, password="hunter2", secret="secret-b" * 8)
    with pytest.raises(auth2.AuthError):
        auth2.verify_token(tok)
