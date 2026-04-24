"""
FreeLLMAPI invoice parser.

FreeLLMAPI currently accepts text-only OpenAI-compatible chat requests, so this
parser first extracts text locally, then asks FreeLLMAPI to produce the bill JSON.
"""
from __future__ import annotations

import json

import httpx

from parser import extract_bill_text

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
            raise RuntimeError(
                f"Model {model} returned non-JSON output. First 200 chars: {text[:200]!r}"
            ) from None
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Model {model} returned JSON that was not an object.")
    return parsed


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
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": f"Invoice text:\n\n{invoice_text}"},
        ],
    }

    with httpx.Client(timeout=90.0) as client:
        response = client.post(_chat_completions_url(base_url), headers=headers, json=payload)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            detail = response.json()
        except json.JSONDecodeError:
            detail = response.text
        raise RuntimeError(f"FreeLLMAPI request failed: {detail}") from e

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
