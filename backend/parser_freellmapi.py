"""
FreeLLMAPI invoice parser.

FreeLLMAPI currently accepts text-only OpenAI-compatible chat requests, so this
parser first extracts text locally, then asks FreeLLMAPI to produce the bill JSON.

Multi-bill batches on free-tier provider keys often hit per-minute rate limits
(Gemini free is ~10 RPM). We absorb those with bounded retries and a clearer
error message so the user knows what to wait for.
"""
from __future__ import annotations

import json
import logging
import os
import time

import httpx

from parser import extract_bill_text

logger = logging.getLogger("utility_tracker")

# Big enough for korteriühistu bills with 15+ line items + Estonian/English
# translations. Override with FREELLMAPI_MAX_TOKENS if a future format needs more.
DEFAULT_MAX_TOKENS = int(os.environ.get("FREELLMAPI_MAX_TOKENS", 10000))

# Retry configuration for transient errors (rate limits, provider exhaustion,
# upstream 5xx). These tend to clear within seconds; a small backoff usually
# rescues a multi-file upload that would otherwise show partial failures.
MAX_RETRIES = int(os.environ.get("FREELLMAPI_MAX_RETRIES", 3))
RETRY_BASE_DELAY_SEC = float(os.environ.get("FREELLMAPI_RETRY_BASE_DELAY_SEC", 4.0))

_EXTRACTION_PROMPT = """You are an expert at reading invoices and bills of any type: utilities
(electricity, gas, water, heating, internet, waste), subscriptions, services, rent,
housing association fees, or any other kind.

Extract structured data from the invoice text below. Return ONLY a valid JSON object:
{
  "provider": "issuing company or supplier name",
  "utility_type": "best-fit category: electricity, gas, water, heating, internet, waste, other",
  "amount_eur": numeric total amount due (use the invoice currency; convert symbol to number if needed),
  "consumption_kwh": numeric kWh consumed if applicable (null otherwise),
  "consumption_m3": numeric cubic metres consumed if applicable (null otherwise),
  "bill_date": "YYYY-MM-DD invoice date",
  "period_start": "YYYY-MM-DD billing period start (null if not shown)",
  "period_end": "YYYY-MM-DD billing period end (null if not shown)",
  "account_number": "customer / account / contract number",
  "address": "service or billing address",
  "period": "raw period text exactly as printed on the invoice; do NOT translate",
  "vat_amount": numeric VAT/tax amount,
  "amount_without_vat": numeric subtotal before VAT/tax,
  "meter_reading_start": numeric opening meter reading if shown,
  "meter_reading_end": numeric closing meter reading if shown,
  "due_date": "YYYY-MM-DD payment due date",
  "line_items": [
    {
      "description_et": "line item description exactly as printed on the invoice",
      "description_en": "English translation or plain-English rephrasing of the description",
      "amount_eur": numeric line amount,
      "quantity": numeric quantity,
      "unit": "unit of measure (kWh, m3, pcs, months, etc.)"
    }
  ],
  "confidence": "high/medium/low"
}

List every charge line visible. Use null for any field you cannot determine.
Return only the JSON."""


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _looks_truncated(text: str) -> bool:
    """Heuristic: an LLM response that hit max_tokens usually ends mid-token,
    so we never see a closing brace and may end on a partial value."""
    stripped = text.rstrip()
    if not stripped:
        return False
    if stripped.endswith("}"):
        return False
    # Counts of unmatched braces or unclosed strings are a strong signal.
    opens = stripped.count("{")
    closes = stripped.count("}")
    return opens > closes


def _loads_json_from_model(text: str, model: str) -> dict:
    text = text.strip()
    if not text:
        raise RuntimeError(f"Model {model} returned an empty response.")

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            if _looks_truncated(text):
                raise RuntimeError(
                    f"Model {model} hit its output token limit before finishing the JSON. "
                    f"Try a larger model or set FREELLMAPI_MAX_TOKENS higher (currently "
                    f"{DEFAULT_MAX_TOKENS}). First 200 chars: {text[:200]!r}"
                ) from None
            raise RuntimeError(
                f"Model {model} returned non-JSON output. First 200 chars: {text[:200]!r}"
            ) from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Model {model} returned malformed JSON: {e}. First 200 chars: {text[:200]!r}"
            ) from e

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Model {model} returned JSON that was not an object.")
    return parsed


def _is_rate_limit_response(status_code: int, body: object) -> bool:
    """A rate-limit error from any layer in the stack — Gemini, FreeLLMAPI's
    own router, or the OpenAI-compatible glue. Treated as retryable."""
    if status_code == 429:
        return True
    if not isinstance(body, dict):
        return False
    err = body.get("error") if isinstance(body.get("error"), dict) else {}
    err_type = (err.get("type") or "").lower()
    err_msg = (err.get("message") or "").lower()
    if err_type in {"rate_limit_error", "routing_error"}:
        return True
    if "rate limit" in err_msg or "exhausted" in err_msg or "429" in err_msg:
        return True
    return False


def _is_transient_status(status_code: int) -> bool:
    """5xx and a couple of well-known transient codes from upstream proxies."""
    return status_code == 408 or status_code == 425 or 500 <= status_code <= 599


def _friendly_rate_limit_error(detail: object) -> str:
    """Build the single-line message we surface back to the UI when the
    final retry has failed because of upstream rate limits."""
    upstream = ""
    if isinstance(detail, dict):
        err = detail.get("error") if isinstance(detail.get("error"), dict) else {}
        upstream = err.get("message") or ""
    suffix = f" Upstream said: {upstream}" if upstream else ""
    return (
        "Provider rate limit hit and retries exhausted. Wait ~1 minute or add "
        "another provider key to FreeLLMAPI so the router can fall over."
        + suffix
    )


def parse_bill_with_freellmapi(
    file_path: str,
    base_url: str,
    api_key: str | None = None,
    model: str = "auto",
) -> dict:
    extracted = extract_bill_text(file_path)
    invoice_text = extracted.text.strip()
    if len(invoice_text) < 20:
        raise RuntimeError("Local text extraction produced too little text for FreeLLMAPI.")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": f"Invoice text:\n\n{invoice_text}"},
        ],
    }

    response: httpx.Response | None = None
    last_detail: object = None
    with httpx.Client(timeout=120.0) as client:
        for attempt in range(MAX_RETRIES + 1):
            response = client.post(_chat_completions_url(base_url), headers=headers, json=payload)
            if response.is_success:
                break

            try:
                last_detail = response.json()
            except json.JSONDecodeError:
                last_detail = response.text

            transient = _is_rate_limit_response(response.status_code, last_detail) \
                or _is_transient_status(response.status_code)
            if not transient or attempt >= MAX_RETRIES:
                break

            # Honor the upstream Retry-After header when present, otherwise
            # back off exponentially: 4s, 8s, 16s.
            retry_after = response.headers.get("retry-after")
            try:
                wait = float(retry_after) if retry_after else RETRY_BASE_DELAY_SEC * (2 ** attempt)
            except ValueError:
                wait = RETRY_BASE_DELAY_SEC * (2 ** attempt)
            wait = min(wait, 30.0)
            logger.info(
                "FreeLLMAPI returned %s on attempt %d/%d, retrying in %.1fs",
                response.status_code, attempt + 1, MAX_RETRIES + 1, wait,
            )
            time.sleep(wait)

    assert response is not None  # the loop runs at least once
    if not response.is_success:
        if _is_rate_limit_response(response.status_code, last_detail):
            raise RuntimeError(_friendly_rate_limit_error(last_detail))
        raise RuntimeError(f"FreeLLMAPI request failed: {last_detail}")

    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"FreeLLMAPI returned an unexpected response shape: {body}") from e

    parsed = _loads_json_from_model(str(content), model)
    parsed["_source"] = "freellmapi"
    parsed["_text_source"] = extracted.source
    parsed["_model_used"] = model
    routed_via = response.headers.get("x-routed-via")
    if routed_via:
        parsed["_routed_via"] = routed_via
    return parsed
