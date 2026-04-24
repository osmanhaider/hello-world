"""
Seed the DB with the three Tehnika TN 22 korteriühistu bills
so the dashboard can be previewed without any API calls.
"""
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from translation import enrich_parsed

DB_PATH = "bills.db"

BILLS = [
    # ─── January 2026 (Invoice 1520) ───────────────────────────────────────
    {
        "provider": "Tehnika TN 22 Korteriühistu",
        "utility_type": "other",
        "amount_eur": 294.46,
        "bill_date": "2026-02-09",
        "due_date": "2026-02-23",
        "period": "Jaanuar 2026",
        "period_start": None,
        "period_end": None,
        "account_number": "1520",
        "address": "Tehnika 22-6, Tallinn 10149",
        "consumption_kwh": 124,
        "line_items": [
            {"description_et": "Haldusteenus",                          "amount_eur": 12.19,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Raamatupidamisteenus",                  "amount_eur":  5.23,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Tehnosüsteemide hooldusteenus",         "amount_eur": 15.88,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Sise-ja väliskoristus",                 "amount_eur": 36.40,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Prügivedu",                             "amount_eur": 10.25,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldelekter",                            "amount_eur": 45.15,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldvesi",                               "amount_eur": -0.92,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Küte",                                  "amount_eur":102.95,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Elekter päevane Alg: 9494 Löpp: 9559",  "amount_eur": 18.53,  "quantity": 65.00, "unit": "kwh"},
            {"description_et": "Elekter öine Alg: 8762 Löpp: 8821",     "amount_eur": 15.58,  "quantity": 59.00, "unit": "kwh"},
            {"description_et": "Külm vesi Alg: 439 Löpp: 440",          "amount_eur":  2.60,  "quantity":  1.00, "unit": "m3"},
            {"description_et": "Soe vesi Alg: 217,700 Löpp: 218",       "amount_eur":  0.78,  "quantity":  0.30, "unit": "m3"},
            {"description_et": "Vee soojendamine",                      "amount_eur":  1.68,  "quantity":  0.30, "unit": "m3"},
            {"description_et": "Remondifond",                           "amount_eur": 28.16,  "quantity": 70.40, "unit": "m2"},
        ],
    },
    # ─── February 2026 (Invoice 1535) ──────────────────────────────────────
    {
        "provider": "Tehnika TN 22 Korteriühistu",
        "utility_type": "other",
        "amount_eur": 308.77,
        "bill_date": "2026-03-09",
        "due_date": "2026-03-23",
        "period": "Veebruar 2026",
        "period_start": None,
        "period_end": None,
        "account_number": "1535",
        "address": "Tehnika 22-6, Tallinn 10149",
        "consumption_kwh": 159,
        "line_items": [
            {"description_et": "Haldusteenus",                          "amount_eur": 12.19,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Raamatupidamisteenus",                  "amount_eur":  5.23,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Tehnosüsteemide hooldusteenus",         "amount_eur": 15.88,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Sise-ja väliskoristus",                 "amount_eur": 36.40,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Porivaiba renditeenus",                 "amount_eur":  2.69,  "quantity": 70.40, "unit": "krt"},
            {"description_et": "Prügivedu",                             "amount_eur":  9.60,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldelekter",                            "amount_eur": 45.26,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldvesi",                               "amount_eur": -0.63,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Küte",                                  "amount_eur": 87.27,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Elekter päevane Alg: 9559 Löpp: 9644",  "amount_eur": 24.31,  "quantity": 85.00, "unit": "kwh"},
            {"description_et": "Elekter öine Alg: 8821 Löpp: 8895",     "amount_eur": 19.61,  "quantity": 74.00, "unit": "kwh"},
            {"description_et": "Külm vesi Alg: 440 Löpp: 443,500",      "amount_eur":  9.11,  "quantity":  3.50, "unit": "m3"},
            {"description_et": "Soe vesi Alg: 218 Löpp: 219,600",       "amount_eur":  4.17,  "quantity":  1.60, "unit": "m3"},
            {"description_et": "Vee soojendamine",                      "amount_eur":  8.98,  "quantity":  1.60, "unit": "m3"},
            {"description_et": "Remondifond",                           "amount_eur": 28.16,  "quantity": 70.40, "unit": "m2"},
        ],
    },
    # ─── March 2026 (Invoice 1550) ─────────────────────────────────────────
    {
        "provider": "Tehnika TN 22 Korteriühistu",
        "utility_type": "other",
        "amount_eur": 217.29,
        "bill_date": "2026-04-13",
        "due_date": "2026-04-23",
        "period": "Märts 2026",
        "period_start": None,
        "period_end": None,
        "account_number": "1550",
        "address": "Tehnika 22-6, Tallinn 10149",
        "consumption_kwh": 158,
        "line_items": [
            {"description_et": "Haldusteenus",                          "amount_eur": 12.19,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Raamatupidamisteenus",                  "amount_eur":  5.23,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Tehnosüsteemide hooldusteenus",         "amount_eur": 15.88,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Sise-ja väliskoristus",                 "amount_eur": 36.40,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Porivaiba renditeenus",                 "amount_eur":  5.38,  "quantity": 70.40, "unit": "krt"},
            {"description_et": "Prügivedu",                             "amount_eur": 10.90,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldelekter",                            "amount_eur": 16.80,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Üldvesi",                               "amount_eur": -1.06,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Küte",                                  "amount_eur": 45.75,  "quantity": 70.40, "unit": "m2"},
            {"description_et": "Elekter päevane Alg: 9644 Löpp: 9726",  "amount_eur": 13.94,  "quantity": 82.00, "unit": "kwh"},
            {"description_et": "Elekter öine Alg: 8895 Löpp: 8971",     "amount_eur": 11.40,  "quantity": 76.00, "unit": "kwh"},
            {"description_et": "Külm vesi Alg: 443,500 Löpp: 446,200",  "amount_eur":  7.03,  "quantity":  2.70, "unit": "m3"},
            {"description_et": "Soe vesi Alg: 219,600 Löpp: 220,600",   "amount_eur":  2.60,  "quantity":  1.00, "unit": "m3"},
            {"description_et": "Vee soojendamine",                      "amount_eur":  5.61,  "quantity":  1.00, "unit": "m3"},
            {"description_et": "Remondifond",                           "amount_eur": 28.16,  "quantity": 70.40, "unit": "m2"},
        ],
    },
]


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id TEXT PRIMARY KEY,
            filename TEXT,
            upload_date TEXT,
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
    # Clear any previous demo rows
    c.execute("DELETE FROM bills WHERE provider LIKE '%Tehnika TN 22%'")

    for bill in BILLS:
        enriched = enrich_parsed(bill)
        c.execute("""
            INSERT INTO bills (id, filename, upload_date, bill_date, provider, utility_type,
                amount_eur, consumption_kwh, consumption_m3, period_start, period_end,
                account_number, address, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            f"demo_{bill['account_number']}.pdf",
            datetime.utcnow().isoformat(),
            enriched.get("bill_date"),
            enriched.get("provider"),
            enriched.get("utility_type"),
            enriched.get("amount_eur"),
            enriched.get("consumption_kwh"),
            enriched.get("consumption_m3"),
            enriched.get("period_start"),
            enriched.get("period_end"),
            enriched.get("account_number"),
            enriched.get("address"),
            json.dumps(enriched),
        ))
    conn.commit()
    conn.close()
    print(f"Seeded {len(BILLS)} demo bills.")


if __name__ == "__main__":
    main()
