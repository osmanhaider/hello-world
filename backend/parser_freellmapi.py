"""
FreeLLMAPI invoice parser.

Routes a bill's locally-extracted text through FreeLLMAPI's OpenAI-compatible
proxy so the router can pick whichever free provider key is healthy at the
moment. The HTTP/retry/JSON logic lives in `parser_openai_compat.py` and is
shared with the BYOK path.
"""
from __future__ import annotations

from parser import extract_bill_text
from parser_openai_compat import call_openai_compat_chat


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

    parsed, headers = call_openai_compat_chat(
        invoice_text,
        base_url=base_url,
        api_key=api_key,
        model=model,
        source_name="FreeLLMAPI",
    )
    parsed["_source"] = "freellmapi"
    parsed["_text_source"] = extracted.source
    parsed["_model_used"] = model
    routed_via = headers.get("x-routed-via")
    if routed_via:
        parsed["_routed_via"] = routed_via
    return parsed
