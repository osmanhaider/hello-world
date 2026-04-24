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
from translation import enrich_parsed

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
                    {"type": "text", "text": "This is a PDF utility bill. " + prompt}
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
        parsed = parse_bill_with_claude(save_path)
        parsed = enrich_parsed(parsed)  # add translations locally — no extra API call
    except Exception as e:
        parsed = {"error": str(e)}

    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
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
            json.dumps(parsed)
        ))
        await db.commit()

    return {"id": bill_id, "parsed": parsed}


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

        async with db.execute("""
            SELECT
                utility_type,
                COUNT(*) as bill_count,
                SUM(amount_eur) as total_eur,
                AVG(amount_eur) as avg_eur,
                MIN(amount_eur) as min_eur,
                MAX(amount_eur) as max_eur,
                SUM(consumption_kwh) as total_kwh,
                SUM(consumption_m3) as total_m3
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY utility_type
        """) as c:
            by_type = [dict(r) for r in await c.fetchall()]

        async with db.execute("""
            SELECT
                strftime('%Y-%m', COALESCE(bill_date, upload_date)) as month,
                utility_type,
                SUM(amount_eur) as total_eur,
                COUNT(*) as bill_count
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY month, utility_type
            ORDER BY month
        """) as c:
            by_month = [dict(r) for r in await c.fetchall()]

        async with db.execute("""
            SELECT
                strftime('%Y', COALESCE(bill_date, upload_date)) as year,
                utility_type,
                SUM(amount_eur) as total_eur,
                AVG(amount_eur) as avg_monthly_eur,
                COUNT(*) as bill_count
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY year, utility_type
            ORDER BY year
        """) as c:
            by_year = [dict(r) for r in await c.fetchall()]

        async with db.execute("""
            SELECT
                strftime('%m', COALESCE(bill_date, upload_date)) as month_num,
                AVG(amount_eur) as avg_eur,
                utility_type
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY month_num, utility_type
            ORDER BY month_num
        """) as c:
            seasonal = [dict(r) for r in await c.fetchall()]

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
                strftime('%Y-%m', COALESCE(bill_date, upload_date)) as month,
                SUM(amount_eur) as total_eur
            FROM bills
            WHERE amount_eur IS NOT NULL
            GROUP BY month
            ORDER BY month
        """) as c:
            monthly_total = [dict(r) for r in await c.fetchall()]

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
    line_item_trends: list[dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT bill_date, upload_date, raw_json FROM bills WHERE raw_json IS NOT NULL"
        ) as c:
            bill_rows = await c.fetchall()

    for row in bill_rows:
        date_str = row["bill_date"] or row["upload_date"]
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
            unit_price = round(amount / qty, 4) if qty and qty != 0 else None
            line_item_trends.append({
                "month": month,
                "description_en": en,
                "description_et": et,
                "amount_eur": round(amount, 2),
                "quantity": qty,
                "unit": unit,
                "unit_price": unit_price,
            })

    # Sort so frontend always gets chronological order
    line_item_trends.sort(key=lambda r: (r["month"], r["description_en"]))

    return {
        "by_type": by_type,
        "by_month": by_month,
        "by_year": by_year,
        "seasonal": seasonal,
        "by_provider": by_provider,
        "monthly_total": monthly_total,
        "line_item_trends": line_item_trends,
    }
