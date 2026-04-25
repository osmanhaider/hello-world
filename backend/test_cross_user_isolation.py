"""End-to-end test that confirms one user cannot read, edit, or delete
another user's bills.

We talk to the FastAPI app via TestClient and skip the Google ID-token
exchange by minting app session tokens directly. That keeps the test
focused on the authorization layer (the `AND user_id = ?` SQL gate) and
independent of Google's network identity service.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    """A TestClient bound to a fresh temp DB and uploads dir."""
    tmpdir = Path(tempfile.mkdtemp(prefix="utility-test-"))
    monkeypatch.setenv("AUTH_SECRET", "x" * 64)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("DB_PATH", str(tmpdir / "bills.db"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmpdir / "uploads"))
    monkeypatch.setenv("PARSER_BACKEND", "tesseract")

    # Reload `auth` and `main` so they pick up the patched env vars.
    import auth
    importlib.reload(auth)
    if "main" in sys.modules:
        del sys.modules["main"]
    import main as main_mod
    return main_mod, TestClient(main_mod.app)


def _seed_bill(main_mod, *, owner: str, bill_id: str = "alice-bill-1") -> None:
    """Insert a bill row directly into the DB so the test doesn't have to
    drive the upload pipeline (which needs a real PDF + Tesseract)."""
    async def _insert():
        async with main_mod._db() as db:
            await db.execute(
                "INSERT INTO bills (id, filename, upload_date, provider, "
                "amount_eur, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (bill_id, "fake.pdf", "2026-04-01T00:00:00", "Alice Co", 42.5, owner),
            )
            await db.commit()
    asyncio.run(main_mod.init_db())
    asyncio.run(_insert())


def _bearer(main_mod, sub: str, email: str) -> dict:
    token = main_mod.auth_mod.create_token(sub=sub, email=email, name=email)
    return {"Authorization": f"Bearer {token}"}


def test_other_user_cannot_read_a_bill(client):
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub")
    r = c.get("/api/bills/alice-bill-1", headers=_bearer(main_mod, "bob-sub", "bob@x"))
    assert r.status_code == 404


def test_other_user_cannot_delete_a_bill(client):
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub")
    r = c.delete(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "bob-sub", "bob@x"),
    )
    assert r.status_code == 404
    # And the row is still in the DB for Alice.
    r2 = c.get(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "alice-sub", "alice@x"),
    )
    assert r2.status_code == 200


def test_other_user_cannot_edit_a_bill(client):
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub")
    r = c.put(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "bob-sub", "bob@x"),
        json={"provider": "Hijacked"},
    )
    assert r.status_code == 404
    # The provider in the DB is still Alice's value.
    r2 = c.get(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "alice-sub", "alice@x"),
    )
    assert r2.status_code == 200
    assert r2.json()["provider"] == "Alice Co"


def test_other_user_cannot_flip_private_flag(client):
    """The `is_private` toggle goes through the same PUT path — same gate."""
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub")
    r = c.put(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "bob-sub", "bob@x"),
        json={"is_private": True},
    )
    assert r.status_code == 404


def test_owner_can_still_delete_their_own_bill(client):
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub")
    r = c.delete(
        "/api/bills/alice-bill-1",
        headers=_bearer(main_mod, "alice-sub", "alice@x"),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"


def test_listing_bills_only_returns_callers_own(client):
    """`GET /api/bills` should never include another user's bills."""
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub", bill_id="alice-1")
    _seed_bill(main_mod, owner="bob-sub", bill_id="bob-1")
    r = c.get("/api/bills", headers=_bearer(main_mod, "alice-sub", "alice@x"))
    assert r.status_code == 200
    ids = {b["id"] for b in r.json()}
    assert ids == {"alice-1"}


def test_community_bills_excludes_private_ones(client):
    """A bill marked private must never show up in /api/community/bills."""
    main_mod, c = client
    _seed_bill(main_mod, owner="alice-sub", bill_id="alice-pub")
    _seed_bill(main_mod, owner="alice-sub", bill_id="alice-priv")
    # Mark the second one private (Alice editing her own bill — allowed).
    r = c.put(
        "/api/bills/alice-priv",
        headers=_bearer(main_mod, "alice-sub", "alice@x"),
        json={"is_private": True},
    )
    assert r.status_code == 200

    r = c.get("/api/community/bills", headers=_bearer(main_mod, "bob-sub", "bob@x"))
    assert r.status_code == 200
    ids = {b["id"] for b in r.json()}
    assert "alice-pub" in ids
    assert "alice-priv" not in ids
