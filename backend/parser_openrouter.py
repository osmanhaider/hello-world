"""
OpenRouter invoice parser — uses the OpenAI-compatible OpenRouter API.

Supports any vision model available on OpenRouter (free or paid).
PDF files are rendered to a PNG image first because most free vision models
only accept image inputs, not raw PDF bytes.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile

_EXTRACTION_PROMPT = """You are an expert at reading invoices and bills of any type — utilities \
(electricity, gas, water, heating, internet, waste), subscriptions, services, rent, \
housing association fees, or any other kind.

Extract structured data from this invoice image. Return ONLY a valid JSON object:
{
  "provider": "issuing company or supplier name",
  "utility_type": "best-fit category — one of: electricity, gas, water, heating, internet, waste, other",
  "amount_eur": numeric total amount due (use the invoice currency; convert symbol to number if needed),
  "consumption_kwh": numeric kWh consumed if applicable (null otherwise),
  "consumption_m3": numeric m³ consumed if applicable (null otherwise),
  "bill_date": "YYYY-MM-DD invoice date",
  "period_start": "YYYY-MM-DD billing period start (null if not shown)",
  "period_end": "YYYY-MM-DD billing period end (null if not shown)",
  "account_number": "customer / account / contract number",
  "address": "service or billing address",
  "period": "raw period text exactly as printed on the invoice — do NOT translate",
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
      "unit": "unit of measure (kWh, m³, pcs, months, etc.)"
    }
  ],
  "confidence": "high/medium/low"
}

List every charge line visible. Use null for any field you cannot determine. Return only the JSON."""


def _pdf_to_png(pdf_path: str) -> str:
    """Render the first page of a PDF to a temp PNG. Caller must delete it."""
    from pdf2image import convert_from_path

    pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pages[0].save(tmp.name, "PNG")
    tmp.close()
    return tmp.name


def _b64_data_url(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"


def parse_bill_with_openrouter(
    file_path: str,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Extract invoice data via OpenRouter's OpenAI-compatible API."""
    from openai import OpenAI

    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY must be set for the openrouter parser.")

    chosen_model = model or os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

    client = OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/osmanhaider/ee-utility-trackly",
            "X-Title": "EE Utility Trackly",
        },
    )

    tmp_path: str | None = None
    try:
        if file_path.lower().endswith(".pdf"):
            tmp_path = _pdf_to_png(file_path)
            img_path = tmp_path
        else:
            img_path = file_path

        data_url = _b64_data_url(img_path)

        response = client.chat.completions.create(
            model=chosen_model,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                ],
            }],
        )
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError(
            f"Model {chosen_model} returned an empty response. "
            "Try a different model from the dropdown."
        )

    # Strip markdown fences if the model wrapped the JSON in ```…```
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    # Some vision models emit prose around the JSON. Slice to the first
    # '{' … matching '}' so we can still parse those responses.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(
                f"Model {chosen_model} returned non-JSON output. "
                f"First 200 chars: {text[:200]!r}"
            ) from None
        return json.loads(text[start : end + 1])
