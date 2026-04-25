"""Unit tests for the Google ID-token verifier wrapper."""
from __future__ import annotations

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))


def _reload_module(monkeypatch, *, client_id: str = "test-client-id", allowed: str = ""):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", client_id)
    if allowed:
        monkeypatch.setenv("ALLOWED_EMAILS", allowed)
    else:
        monkeypatch.delenv("ALLOWED_EMAILS", raising=False)
    import google_auth
    return importlib.reload(google_auth)


def _patch_verifier(monkeypatch, payload: dict):
    """Stub out google.oauth2.id_token.verify_oauth2_token to return `payload`."""
    from google.oauth2 import id_token as g_id_token

    def fake_verify(_token, _request, _client_id):
        return payload

    monkeypatch.setattr(g_id_token, "verify_oauth2_token", fake_verify)


def _patch_verifier_raises(monkeypatch, exc: Exception):
    from google.oauth2 import id_token as g_id_token

    def fake_verify(*_args, **_kwargs):
        raise exc

    monkeypatch.setattr(g_id_token, "verify_oauth2_token", fake_verify)


def test_happy_path(monkeypatch):
    g = _reload_module(monkeypatch)
    _patch_verifier(
        monkeypatch,
        {
            "sub": "111",
            "email": "alice@example.com",
            "email_verified": True,
            "name": "Alice",
            "picture": "https://example.com/a.png",
        },
    )
    identity = g.verify_google_id_token("fake.id.token")
    assert identity.sub == "111"
    assert identity.email == "alice@example.com"
    assert identity.name == "Alice"
    assert identity.picture == "https://example.com/a.png"


def test_rejects_unverified_email(monkeypatch):
    g = _reload_module(monkeypatch)
    _patch_verifier(
        monkeypatch,
        {"sub": "111", "email": "alice@example.com", "email_verified": False},
    )
    with pytest.raises(g.GoogleAuthError, match="verified"):
        g.verify_google_id_token("fake.id.token")


def test_requires_client_id(monkeypatch):
    g = _reload_module(monkeypatch, client_id="")
    with pytest.raises(g.GoogleAuthError, match="GOOGLE_CLIENT_ID"):
        g.verify_google_id_token("fake.id.token")


def test_invalid_token_raises(monkeypatch):
    g = _reload_module(monkeypatch)
    _patch_verifier_raises(monkeypatch, ValueError("token expired"))
    with pytest.raises(g.GoogleAuthError, match="invalid Google"):
        g.verify_google_id_token("fake.id.token")


def test_allowlist_blocks_unknown_emails(monkeypatch):
    g = _reload_module(monkeypatch, allowed="me@example.com,friend@example.com")
    _patch_verifier(
        monkeypatch,
        {
            "sub": "111",
            "email": "stranger@example.com",
            "email_verified": True,
            "name": "Stranger",
        },
    )
    with pytest.raises(g.GoogleAuthError, match="allowlist"):
        g.verify_google_id_token("fake.id.token")


def test_allowlist_admits_known_emails(monkeypatch):
    g = _reload_module(monkeypatch, allowed="me@example.com,friend@example.com")
    _patch_verifier(
        monkeypatch,
        {
            "sub": "222",
            "email": "Friend@example.com",  # case-insensitive
            "email_verified": True,
            "name": "Friend",
        },
    )
    identity = g.verify_google_id_token("fake.id.token")
    assert identity.email == "friend@example.com"
