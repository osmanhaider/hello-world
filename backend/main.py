import os
import json
import base64
import uuid
from datetime import datetime, date
from typing import Optional
import aiosqlite
import anthropic
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from translation import enrich_parsed, classify_line_item
from parser import parse_bill as parse_bill_tesseract

# Parser backend: "tesseract" (default, no API key) or "claude" (uses Anthropic API)
PARSER_BACKEND = os.environ.get("PARSER_BACKEND", "tesseract").lower()

DB_PATH = "bills.db"
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="Estonia Utility Bill Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                bill_date TEXT,
                provider TEXT,
                utility_type TEXT,
                amount_eur REAL,
                consumption_kwh REAL,
                consumption_m3 REAL,
                period_start TEXT,
                period_end TEXT,
                account_number TEXT,
                address TEXT,
                raw_json TEXT,
                notes TEXT
            )
        """)
        await db.commit()


@app.on_event("startup")
async def startup():
    await init_db()


class BillUpdate(BaseModel):
    provider: Optional[str] = None
    utility_type: Optional[str] = None
    amount_eur: Optional[float] = None
    consumption_kwh: Optional[float] = None
    consumption_m3: Optional[float] = None
    bill_date: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    notes: Optional[str] = None


def encode_image(path: str) -> tuple[str, str]:
    ext = path.rsplit(".", 1)[-1].lower()
    media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                 "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf"}
    media_type = media_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def parse_bill_with_claude(file_path: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    data, media_type = encode_image(file_path)

    prompt = """You are an expert at reading Estonian utility bills (electricity, gas, water, heating, internet, etc.).

Extract structured data from this bill image. Return ONLY a valid JSON object:
{
  "provider": "company name (e.g. Eesti Energia, Elektrilevi, Tallinna Vesi, Gasum, Telia)",
  "utility_type": "one of: electricity, gas, water, heating, internet, waste, other",
  "amount_eur": numeric total amount due in euros (e.g. 45.23),
  "consumption_kwh": numeric kWh if electricity/heating bill (null otherwise),
  "consumption_m3": numeric m3 if gas/water bill (null otherwise),
  "bill_date": "YYYY-MM-DD invoice date",
  "period_start": "YYYY-MM-DD billing period start",
  "period_end": "YYYY-MM-DD billing period end",
  "account_number": "customer or account number",
  "address": "service address",
  "period": "raw period text as shown on the bill (e.g. 'Veebruar 2026', 'Märts 2026') — do NOT translate",
  "vat_amount": numeric VAT in euros,
  "amount_without_vat": numeric amount excluding VAT,
  "meter_reading_start": numeric opening meter reading,
  "meter_reading_end": numeric closing meter reading,
  "due_date": "YYYY-MM-DD payment due date",
  "line_items": [
    {
      "description_et": "Estonian line item text exactly as printed (e.g. 'Elektrienergia', 'Võrgutasu', 'Aktsiis')",
      "amount_eur": numeric amount for this line,
      "quantity": numeric quantity,
      "unit": "kWh / m3 / pcs / etc."
    }
  ],
  "confidence": "high/medium/low"
}

List every charge line visible. Use null for any field you cannot read. Return only the JSON."""

    if media_type == "application/pdf":
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": data},
                    },
                    {"type": "text", "text": prompt},
                ]
            }]
        )
    else:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )

    text = message.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


@app.post("/api/bills/upload")
async def upload_bill(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Unsupported file type. Upload an image or PDF.")

    bill_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    save_path = os.path.join(UPLOADS_DIR, f"{bill_id}.{ext}")

    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    try:
        if PARSER_BACKEND == "claude":
            parsed = parse_bill_with_claude(save_path)
        else:
            parsed = parse_bill_tesseract(save_path)
        parsed = enrich_parsed(parsed)  # add translations locally — no API call
    except Exception as e:
        parsed = {"error": str(e), "_source": PARSER_BACKEND}

    now = datetime.utcnow().isoformat()
    provider = parsed.get("provider")
    period_start = parsed.get("period_start")
    account_number = parsed.get("account_number")

    replaced = False
    replaced_id: Optional[str] = None

    async with aiosqlite.connect(DB_PATH) as db:
        # 1st priority: same filename → same physical file uploaded again
        existing_row = None
        async with db.execute(
            "SELECT id, filename FROM bills WHERE filename = ? "
            "ORDER BY upload_date DESC LIMIT 1",
            (file.filename,),
        ) as c:
            existing_row = await c.fetchone()

        # 2nd priority: same provider (case-insensitive) + same billing period
        if not existing_row and provider and period_start:
            async with db.execute(
                "SELECT id, filename FROM bills "
                "WHERE LOWER(TRIM(provider)) = LOWER(TRIM(?)) AND period_start = ? "
                "ORDER BY upload_date DESC LIMIT 1",
                (provider, period_start),
            ) as c:
                existing_row = await c.fetchone()

        # 3rd priority: same provider (case-insensitive) + same account number
        if not existing_row and provider and account_number:
            async with db.execute(
                "SELECT id, filename FROM bills "
                "WHERE LOWER(TRIM(provider)) = LOWER(TRIM(?)) AND account_number = ? "
                "ORDER BY upload_date DESC LIMIT 1",
                (provider, account_number),
            ) as c:
                existing_row = await c.fetchone()

        if existing_row:
            # Overwrite the matching row in place. Keep its id so any links hold.
            replaced = True
            replaced_id = existing_row[0]
            old_filename = existing_row[1]
            # Delete the previously stored file if it was a different one
            if old_filename:
                for ext_try in ("pdf", "png", "jpg", "jpeg", "gif", "webp"):
                    old_path = os.path.join(UPLOADS_DIR, f"{replaced_id}.{ext_try}")
                    if os.path.exists(old_path) and old_path != save_path:
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
            # Rename the newly uploaded file to use the original id so paths stay stable
            new_path = os.path.join(UPLOADS_DIR, f"{replaced_id}.{ext}")
            if new_path != save_path:
                try:
                    os.replace(save_path, new_path)
                    save_path = new_path
                except OSError:
                    pass
            bill_id = replaced_id

            await db.execute("""
                UPDATE bills SET
                    filename = ?, upload_date = ?, bill_date = ?, provider = ?,
                    utility_type = ?, amount_eur = ?, consumption_kwh = ?,
                    consumption_m3 = ?, period_start = ?, period_end = ?,
                    account_number = ?, address = ?, raw_json = ?
                WHERE id = ?
            """, (
                file.filename, now,
                parsed.get("bill_date"),
                parsed.get("provider"),
                parsed.get("utility_type"),
                parsed.get("amount_eur"),
                parsed.get("consumption_kwh"),
                parsed.get("consumption_m3"),
                parsed.get("period_start"),
                parsed.get("period_end"),
                parsed.get("account_number"),
                parsed.get("address"),
                json.dumps(parsed),
                replaced_id,
            ))
        else:
            await db.execute("""
                INSERT INTO bills (id, filename, upload_date, bill_date, provider, utility_type,
                    amount_eur, consumption_kwh, consumption_m3, period_start, period_end,
                    account_number, address, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_id, file.filename, now,
                parsed.get("bill_date"),
                parsed.get("provider"),
                parsed.get("utility_type"),
                parsed.get("amount_eur"),
                parsed.get("consumption_kwh"),
                parsed.get("consumption_m3"),
                parsed.get("period_start"),
                parsed.get("period_end"),
                parsed.get("account_number"),
                parsed.get("address"),
                json.dumps(parsed),
            ))
        await db.commit()

    return {"id": bill_id, "parsed": parsed, "replaced": replaced}


@app.get("/api/bills")
async def list_bills():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bills ORDER BY bill_date DESC, upload_date DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@app.get("/api/bills/{bill_id}")
async def get_bill(bill_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Bill not found")
    return dict(row)


@app.put("/api/bills/{bill_id}")
async def update_bill(bill_id: str, update: BillUpdate):
    fields = {k: v for k, v in update.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [bill_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bills SET {set_clause} WHERE id = ?", values)
        await db.commit()
    return {"status": "updated"}


@app.delete("/api/bills/{bill_id}")
async def delete_bill(bill_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
        await db.commit()
    return {"status": "deleted"}


@app.get("/api/analytics/summary")
async def analytics_summary():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Fetch every bill so we can split korteriühistu bills into their
        # individual line-item categories (electricity, water, heating,
        # waste, building management, …). For single-service bills we
        # attribute the whole amount to the bill's utility_type.
        async with db.execute("""
            SELECT id, utility_type, amount_eur, consumption_kwh, consumption_m3,
                   period_start, bill_date, upload_date, raw_json
            FROM bills
            WHERE amount_eur IS NOT NULL
        """) as c:
            all_bills = [dict(r) for r in await c.fetchall()]

        async with db.execute("""
            SELECT
                provider,
                COUNT(*) as bill_count,
                SUM(amount_eur) as total_eur,
                AVG(amount_eur) as avg_eur
            FROM bills
            WHERE amount_eur IS NOT NULL AND provider IS NOT NULL
            GROUP BY provider
            ORDER BY total_eur DESC
        """) as c:
            by_provider = [dict(r) for r in await c.fetchall()]

        async with db.execute("""
            SELECT
                strftime('%Y-%m', COALESCE(period_start, bill_date, upload_date)) as month,
                SUM(amount_eur) as total_eur
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY month
            ORDER BY month
        """) as c:
            monthly_total = [dict(r) for r in await c.fetchall()]

    # ────────────────────────────────────────────────────────────────────
    # Per-category breakdown.
    # Split each korteriühistu bill (utility_type="other") into its
    # individual line-item categories so the Type Breakdown chart shows a
    # meaningful split instead of one giant "other" slice. Single-service
    # bills contribute their whole amount under their utility_type.
    #
    # We aggregate at the *bill-category* level, not the *line-item* level:
    # a single bill with 3 water line items contributes ONE water entry
    # whose amount is the sum of the 3 lines. That way bill_count and
    # min/max/avg per type remain bill-level stats.
    # ────────────────────────────────────────────────────────────────────
    from collections import defaultdict

    # bill_cat_totals[(bill_id, category)] = summed line-item amount
    bill_cat_totals: dict[tuple[str, str], float] = defaultdict(float)
    bill_meta: dict[str, dict] = {}

    for bill in all_bills:
        date_key = bill["period_start"] or bill["bill_date"] or bill["upload_date"]
        if not date_key or len(date_key) < 7:
            continue
        bid = bill["id"]
        bill_meta[bid] = {
            "month": date_key[:7],
            "year": date_key[:4],
            "month_num": date_key[5:7],
            "utility_type": bill["utility_type"] or "other",
            "amount_eur": bill["amount_eur"],
            "consumption_kwh": bill["consumption_kwh"],
            "consumption_m3": bill["consumption_m3"],
        }
        bill_type = bill["utility_type"] or "other"

        # For korteriühistu bills, split by line-item category; single-
        # service bills attribute their total to the bill's utility_type.
        if bill_type == "other" and bill["raw_json"]:
            try:
                raw = json.loads(bill["raw_json"])
            except (json.JSONDecodeError, TypeError):
                raw = {}
            items = raw.get("line_items") or []
            attributed = False
            for item in items:
                amt = item.get("amount_eur")
                if amt is None:
                    continue
                cat = classify_line_item(item.get("description_et") or "")
                bill_cat_totals[(bid, cat)] += float(amt)
                attributed = True
            if not attributed and bill["amount_eur"] is not None:
                bill_cat_totals[(bid, "other")] = float(bill["amount_eur"])
        elif bill["amount_eur"] is not None:
            bill_cat_totals[(bid, bill_type)] = float(bill["amount_eur"])

    # Build type-level aggregation from bill-category totals
    type_amts: dict[str, list[float]] = defaultdict(list)
    type_kwh: dict[str, float] = defaultdict(float)
    type_m3: dict[str, float] = defaultdict(float)
    type_has_kwh: set[str] = set()
    type_has_m3: set[str] = set()

    month_agg: dict[tuple[str, str], float] = defaultdict(float)
    month_bill_count: dict[tuple[str, str], int] = defaultdict(int)
    year_agg: dict[tuple[str, str], list[float]] = defaultdict(list)
    seasonal_agg: dict[tuple[str, str], list[float]] = defaultdict(list)

    for (bid, cat), amt in bill_cat_totals.items():
        amt_r = round(amt, 2)
        meta = bill_meta[bid]
        type_amts[cat].append(amt_r)
        month_agg[(meta["month"], cat)] += amt_r
        month_bill_count[(meta["month"], cat)] += 1
        year_agg[(meta["year"], cat)].append(amt_r)
        seasonal_agg[(meta["month_num"], cat)].append(amt_r)

    # Consumption attribution: kWh belongs to electricity, m³ belongs to water.
    # For single-service bills, use the bill's own utility_type.
    for bid, meta in bill_meta.items():
        if meta["consumption_kwh"] is not None:
            target = meta["utility_type"] if meta["utility_type"] != "other" else "electricity"
            type_kwh[target] += float(meta["consumption_kwh"])
            type_has_kwh.add(target)
        if meta["consumption_m3"] is not None:
            target = meta["utility_type"] if meta["utility_type"] != "other" else "water"
            type_m3[target] += float(meta["consumption_m3"])
            type_has_m3.add(target)

    def _stats(amts: list[float]) -> dict:
        return {
            "bill_count": len(amts),
            "total_eur": round(sum(amts), 2),
            "avg_eur": round(sum(amts) / len(amts), 2) if amts else 0.0,
            "min_eur": round(min(amts), 2) if amts else 0.0,
            "max_eur": round(max(amts), 2) if amts else 0.0,
        }

    by_type = []
    all_categories = set(type_amts.keys()) | type_has_kwh | type_has_m3
    for utype in sorted(all_categories, key=lambda t: -sum(type_amts.get(t, []))):
        s = _stats(type_amts.get(utype, []))
        by_type.append({
            "utility_type": utype,
            **s,
            "total_kwh": round(type_kwh[utype], 2) if utype in type_has_kwh else None,
            "total_m3": round(type_m3[utype], 2) if utype in type_has_m3 else None,
        })

    by_month = sorted(
        [{"month": m, "utility_type": t, "total_eur": round(v, 2),
          "bill_count": month_bill_count[(m, t)]}
         for (m, t), v in month_agg.items()],
        key=lambda r: (r["month"], r["utility_type"]),
    )

    by_year = sorted(
        [{"year": y, "utility_type": t, "total_eur": round(sum(amts), 2),
          "avg_monthly_eur": round(sum(amts) / len(amts), 2) if amts else 0.0,
          "bill_count": len(amts)}
         for (y, t), amts in year_agg.items()],
        key=lambda r: (r["year"], r["utility_type"]),
    )

    seasonal = sorted(
        [{"month_num": mn, "utility_type": t,
          "avg_eur": round(sum(amts) / len(amts), 2) if amts else 0.0}
         for (mn, t), amts in seasonal_agg.items()],
        key=lambda r: (r["month_num"], r["utility_type"]),
    )

    # Bill-level totals (distinct from by_type which is category-level)
    bill_amounts = [
        float(m["amount_eur"]) for m in bill_meta.values()
        if m["amount_eur"] is not None
    ]
    if bill_amounts:
        totals = {
            "bill_count": len(bill_amounts),
            "total_eur": round(sum(bill_amounts), 2),
            "avg_eur": round(sum(bill_amounts) / len(bill_amounts), 2),
            "min_eur": round(min(bill_amounts), 2),
            "max_eur": round(max(bill_amounts), 2),
        }
    else:
        totals = {"bill_count": 0, "total_eur": 0.0, "avg_eur": 0.0,
                  "min_eur": 0.0, "max_eur": 0.0}

    # Compute rolling 3-month average on total
    for i, row in enumerate(monthly_total):
        window = monthly_total[max(0, i-2):i+1]
        row["rolling_avg_3m"] = sum(r["total_eur"] for r in window) / len(window)

    # MoM delta per month
    for i, row in enumerate(monthly_total):
        prev = monthly_total[i - 1]["total_eur"] if i > 0 else None
        row["mom_delta_eur"] = round(row["total_eur"] - prev, 2) if prev is not None else None
        row["mom_delta_pct"] = round((row["total_eur"] - prev) / prev * 100, 1) if prev else None

    # YoY delta per month
    month_map = {r["month"]: r["total_eur"] for r in monthly_total}
    for row in monthly_total:
        y, m = row["month"].split("-")
        prev_year_key = f"{int(y)-1}-{m}"
        prev = month_map.get(prev_year_key)
        row["yoy_delta_eur"] = round(row["total_eur"] - prev, 2) if prev else None
        row["yoy_delta_pct"] = round((row["total_eur"] - prev) / prev * 100, 1) if prev else None

    # Line-item level trends — extracted from raw_json of every bill
    import re as _re_li
    _suffix_en = _re_li.compile(r"\s*\[Start:.*?\]\s*$")
    _suffix_et = _re_li.compile(r"\s+[Aa]lg[:\s].*$")

    line_item_trends: list[dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT period_start, bill_date, upload_date, raw_json FROM bills WHERE raw_json IS NOT NULL"
        ) as c:
            bill_rows = await c.fetchall()

    for row in bill_rows:
        date_str = row["period_start"] or row["bill_date"] or row["upload_date"]
        if not date_str:
            continue
        month = date_str[:7]
        try:
            data = json.loads(row["raw_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        for item in data.get("line_items") or []:
            en = (item.get("description_en") or "").strip()
            et = (item.get("description_et") or "").strip()
            amount = item.get("amount_eur")
            qty = item.get("quantity")
            unit = (item.get("unit") or "").lower()
            if not en or amount is None:
                continue
            # Strip per-bill meter-reading suffixes so the same item
            # aggregates across months.
            en_key = _suffix_en.sub("", en).strip()
            et_key = _suffix_et.sub("", et).strip()
            unit_price = round(amount / qty, 4) if qty and qty != 0 else None
            line_item_trends.append({
                "month": month,
                "description_en": en_key,
                "description_et": et_key,
                "amount_eur": round(amount, 2),
                "quantity": qty,
                "unit": unit,
                "unit_price": unit_price,
            })

    # Sort so frontend always gets chronological order
    line_item_trends.sort(key=lambda r: (r["month"], r["description_en"]))

    return {
        "totals": totals,
        "by_type": by_type,
        "by_month": by_month,
        "by_year": by_year,
        "seasonal": seasonal,
        "by_provider": by_provider,
        "monthly_total": monthly_total,
        "line_item_trends": line_item_trends,
    }
