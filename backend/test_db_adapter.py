"""Tests for the SQLite/Postgres DB adapter helpers.

These keep the app's SQL-compatibility behavior explicit without needing a
live Supabase instance in CI.
"""
from __future__ import annotations

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_convert_placeholders_to_asyncpg_numbered_params():
    import db

    sql = "SELECT * FROM bills WHERE id = ? AND user_id = ? AND provider LIKE ?"
    assert db.convert_placeholders(sql) == (
        "SELECT * FROM bills WHERE id = $1 AND user_id = $2 AND provider LIKE $3"
    )


def test_backend_selection_uses_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import db

    importlib.reload(db)
    assert db.is_postgres() is False
    assert db.public_condition() == "COALESCE(is_private, 0) = 0"

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    assert db.is_postgres() is True
    assert db.public_condition() == "COALESCE(is_private, false) = false"
    assert db.public_condition("b") == "COALESCE(b.is_private, false) = false"


def test_row_supports_mapping_and_index_access():
    import db

    row = db.Row(["id", "email"], ["u1", "a@example.com"])
    assert row["id"] == "u1"
    assert row[0] == "u1"
    assert row[1] == "a@example.com"
    assert dict(row) == {"id": "u1", "email": "a@example.com"}
