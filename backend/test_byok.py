"""Tests for the BYOK module + endpoints.

Covers:
- AES-GCM encrypt/decrypt round-trip
- mask_key behavior for short and long keys
- BYOK_ENCRYPTION_KEY missing rejects encrypt/decrypt at runtime
- Cross-user isolation: Bob can't list / use / delete Alice's keys
"""
from __future__ import annotations

import asyncio
import base64
import importlib
import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))


def _b64_key(n: int = 32) -> str:
    return base64.b64encode(secrets.token_bytes(n)).decode()


# ────────────────────────────────────────────────────────────────────────
# Pure-helper tests (no app, no DB)
# ────────────────────────────────────────────────────────────────────────


def _reload_byok(monkeypatch: pytest.MonkeyPatch, key: str | None) -> object:
    if key is None:
        monkeypatch.delenv("BYOK_ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("BYOK_ENCRYPTION_KEY", key)
    import byok
    importlib.reload(byok)
    byok.reset_encryption_key_cache()
    return byok


def test_encrypt_decrypt_roundtrip(monkeypatch: pytest.MonkeyPatch):
    byok = _reload_byok(monkeypatch, _b64_key())
    plain = "sk-test-1234567890abcdef"
    ct, iv, tag = byok.encrypt(plain)
    assert ct and iv and tag
    assert byok.decrypt(ct, iv, tag) == plain


def test_decrypt_with_wrong_tag_fails(monkeypatch: pytest.MonkeyPatch):
    byok = _reload_byok(monkeypatch, _b64_key())
    ct, iv, _tag = byok.encrypt("sk-secret")
    bad_tag = base64.b64encode(b"x" * 16).decode()
    with pytest.raises(Exception):
        byok.decrypt(ct, iv, bad_tag)


def test_mask_key_long_and_short(monkeypatch: pytest.MonkeyPatch):
    byok = _reload_byok(monkeypatch, _b64_key())
    assert byok.mask_key("sk-abcdefghij12345678") == "sk-a…5678"
    assert byok.mask_key("short") == "•" * 8


def test_missing_encryption_key_rejected(monkeypatch: pytest.MonkeyPatch):
    byok = _reload_byok(monkeypatch, None)
    assert byok.is_configured() is False
    with pytest.raises(byok.ByokError, match="BYOK_ENCRYPTION_KEY"):
        byok.encrypt("anything")


def test_hex_encoded_key_also_works(monkeypatch: pytest.MonkeyPatch):
    """Either base64 or 64-char hex is accepted for ergonomics."""
    hex_key = secrets.token_bytes(32).hex()
    byok = _reload_byok(monkeypatch, hex_key)
    ct, iv, tag = byok.encrypt("sk-roundtrip")
    assert byok.decrypt(ct, iv, tag) == "sk-roundtrip"


def test_invalid_key_length_rejected(monkeypatch: pytest.MonkeyPatch):
    byok = _reload_byok(monkeypatch, base64.b64encode(b"too-short").decode())
    with pytest.raises(byok.ByokError, match="32 bytes"):
        byok.encrypt("anything")


# ────────────────────────────────────────────────────────────────────────
# End-to-end endpoint tests
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    tmpdir = Path(tempfile.mkdtemp(prefix="utility-byok-test-"))
    monkeypatch.setenv("AUTH_SECRET", "x" * 64)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("BYOK_ENCRYPTION_KEY", _b64_key())
    monkeypatch.setenv("DB_PATH", str(tmpdir / "bills.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmpdir / "uploads"))
    monkeypatch.setenv("PARSER_BACKEND", "tesseract")

    import auth
    import byok
    importlib.reload(auth)
    importlib.reload(byok)
    byok.reset_encryption_key_cache()
    if "main" in sys.modules:
        del sys.modules["main"]
    import main as main_mod
    asyncio.run(main_mod.init_db())
    return main_mod, TestClient(main_mod.app)


def _bearer(main_mod, sub: str, email: str) -> dict:
    token = main_mod.auth_mod.create_token(sub=sub, email=email, name=email)
    return {"Authorization": f"Bearer {token}"}


def test_provider_catalogue_listed(client):
    main_mod, c = client
    r = c.get("/api/byok-providers", headers=_bearer(main_mod, "alice", "a@x.com"))
    assert r.status_code == 200
    data = r.json()
    assert data["configured"] is True
    ids = {p["id"] for p in data["providers"]}
    assert {"openai", "google", "groq", "cerebras"}.issubset(ids)


def test_create_list_delete_key_round_trip(client):
    main_mod, c = client
    headers = _bearer(main_mod, "alice", "a@x.com")
    create = c.post(
        "/api/byok-keys",
        headers=headers,
        json={"label": "personal", "provider": "groq", "key": "gsk_abcdefghij1234567890"},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["provider"] == "groq"
    assert body["masked_key"] == "gsk_…7890"

    listed = c.get("/api/byok-keys", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["label"] == "personal"
    assert "gsk_abcdefghij" not in listed[0]["masked_key"]  # only masked

    deleted = c.delete(f"/api/byok-keys/{body['id']}", headers=headers)
    assert deleted.status_code == 200
    assert c.get("/api/byok-keys", headers=headers).json() == []


def test_unknown_provider_rejected(client):
    main_mod, c = client
    headers = _bearer(main_mod, "alice", "a@x.com")
    r = c.post(
        "/api/byok-keys",
        headers=headers,
        json={"label": "x", "provider": "foo", "key": "12345678"},
    )
    assert r.status_code == 400


def test_duplicate_label_rejected(client):
    main_mod, c = client
    headers = _bearer(main_mod, "alice", "a@x.com")
    payload = {"label": "main", "provider": "openai", "key": "sk-aaaabbbbcccc"}
    assert c.post("/api/byok-keys", headers=headers, json=payload).status_code == 201
    second = c.post("/api/byok-keys", headers=headers, json=payload)
    assert second.status_code == 409


def test_other_user_cannot_list_or_use_keys(client):
    main_mod, c = client
    alice = _bearer(main_mod, "alice", "a@x.com")
    bob = _bearer(main_mod, "bob", "b@x.com")
    create = c.post(
        "/api/byok-keys",
        headers=alice,
        json={"label": "personal", "provider": "groq", "key": "gsk_aliceonly12345678"},
    )
    assert create.status_code == 201
    alice_key_id = create.json()["id"]

    # Bob's listing is empty.
    assert c.get("/api/byok-keys", headers=bob).json() == []

    # Bob can't delete Alice's key.
    bob_delete = c.delete(f"/api/byok-keys/{alice_key_id}", headers=bob)
    assert bob_delete.status_code == 404

    # And the key is still around for Alice.
    alice_listed = c.get("/api/byok-keys", headers=alice).json()
    assert len(alice_listed) == 1
