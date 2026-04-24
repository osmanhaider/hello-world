"""Unit tests for the Claude parser branch.

No network calls. The Anthropic SDK client is replaced with a fake that
returns a canned JSON response, so we can verify that the request shape
is correct (document content block for PDF, image block for image) and
that the JSON-extraction glue around it works.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import types
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(__file__))


def _fake_response(payload: dict):
    content = types.SimpleNamespace(text=json.dumps(payload))
    return types.SimpleNamespace(content=[content])


@pytest.fixture()
def fake_anthropic(monkeypatch):
    """Replace the cached Claude client with a mock for each test."""
    import main  # noqa: E402

    main._claude_client = None  # reset the cache between tests
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")

    mock_client = mock.MagicMock()
    main._claude_client = mock_client  # short-circuit the lazy init
    return mock_client


def _write_tmp_file(suffix: str, contents: bytes = b"pretend-bytes") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(contents)
    return path


def test_pdf_sends_document_content_block(fake_anthropic):
    import main

    fake_anthropic.messages.create.return_value = _fake_response({
        "provider": "Acme Co",
        "amount_eur": 12.34,
        "line_items": [],
    })
    pdf_path = _write_tmp_file(".pdf", b"%PDF-1.4 fake")
    try:
        result = main.parse_bill_with_claude(pdf_path)
    finally:
        os.remove(pdf_path)

    assert result["provider"] == "Acme Co"
    assert result["amount_eur"] == 12.34

    call = fake_anthropic.messages.create.call_args
    content = call.kwargs["messages"][0]["content"]
    # Must include a document block with base64-encoded PDF bytes.
    doc = next(b for b in content if b.get("type") == "document")
    assert doc["source"]["media_type"] == "application/pdf"
    assert base64.b64decode(doc["source"]["data"]) == b"%PDF-1.4 fake"


def test_image_sends_image_content_block(fake_anthropic):
    import main

    fake_anthropic.messages.create.return_value = _fake_response({"provider": "X"})
    img_path = _write_tmp_file(".png", b"\x89PNG fake")
    try:
        main.parse_bill_with_claude(img_path)
    finally:
        os.remove(img_path)

    call = fake_anthropic.messages.create.call_args
    content = call.kwargs["messages"][0]["content"]
    img = next(b for b in content if b.get("type") == "image")
    assert img["source"]["media_type"] == "image/png"


def test_strips_markdown_code_fence(fake_anthropic):
    """Claude sometimes wraps JSON in ```json ... ``` — the parser must unwrap it."""
    import main

    fenced = "```json\n" + json.dumps({"provider": "Fenced"}) + "\n```"
    fake_anthropic.messages.create.return_value = types.SimpleNamespace(
        content=[types.SimpleNamespace(text=fenced)]
    )
    img_path = _write_tmp_file(".png")
    try:
        result = main.parse_bill_with_claude(img_path)
    finally:
        os.remove(img_path)
    assert result["provider"] == "Fenced"


def test_missing_api_key_raises(monkeypatch):
    import main

    main._claude_client = None
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        main._get_claude_client()
