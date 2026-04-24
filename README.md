# Estonia Utility Bill Tracker

Upload monthly utility bills (images or PDFs), get them parsed and translated from Estonian to English automatically, and explore spending patterns through a 12-section analytics dashboard.

Runs **entirely locally** — no API key required.

## Features

- **Open-source extraction**: Tesseract OCR for images, `pdfplumber` for native-text PDFs, `pdf2image` + OCR fallback for scanned PDFs
- **Hardcoded Estonian→English dictionary** (~180 terms) — no API call needed for translation
  - Utility services: electricity, gas, water, heating, telecom, waste
  - Korteriühistu line items: Haldusteenus, Küte, Remondifond, Tehnosüsteemide hooldusteenus…
  - Months (Jaanuar → January), weekdays, units, invoice field labels
  - Inline meter-reading format: `Alg: 9644 Löpp: 9726` → `[Start: 9644, End: 9726]`
- **12-section analytics dashboard** with trends, MoM/YoY %, unit-price tracking, price-vs-consumption decomposition
- **One-click PDF export** of the whole dashboard (client-side, no server round-trip)
- **Optional Claude API fallback** for higher-accuracy extraction, toggled by `PARSER_BACKEND=claude`

## Architecture

```
┌────────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│  React + Vite UI   │ ───► │  FastAPI backend    │ ───► │  SQLite (bills) │
│  (Recharts, TSX)   │ ◄─── │  /api/bills/upload  │ ◄─── │                 │
└────────────────────┘      │  /api/analytics/... │      └─────────────────┘
                            └─────────┬───────────┘
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
              ┌─────────────────┐           ┌────────────────┐
              │  parser.py      │           │ translation.py │
              │  Tesseract OCR  │           │ 180-term EST   │
              │  pdfplumber     │           │ dictionary     │
              └─────────────────┘           └────────────────┘
```

## Quick start

### 1. System dependencies

```bash
# Tesseract with Estonian language pack
sudo apt-get install -y tesseract-ocr tesseract-ocr-est tesseract-ocr-eng \
                        poppler-utils
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn python-multipart anthropic aiosqlite \
                      pillow pdf2image pytesseract pdfplumber

# Start the server (no API key needed — uses Tesseract by default)
./venv/bin/uvicorn main:app --port 8000
```

Backend env vars:
- `PARSER_BACKEND=tesseract` *(default)* — open-source, local, no API key
- `PARSER_BACKEND=claude` — Anthropic Claude API (requires `ANTHROPIC_API_KEY`)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 4. Optional: seed demo data

Three synthetic korteriühistu bills to see the dashboard populated:

```bash
cd backend && ./venv/bin/python seed_demo.py
```

## Parser accuracy

Tested on real Tallinn korteriühistu invoices:

| Bill | Line items | Extraction | Total match |
|---|---|---|---|
| December 2025 | 11 | 11 / 11 | ✓ €208.49 exact |
| January 2026  | 14 | 14 / 14 | ✓ €294.46 exact |
| February 2026 | 15 | 15 / 15 | ✓ €308.77 exact |
| March 2026    | 15 | 15 / 15 | ✓ €217.29 exact |

Native-text PDFs give **high confidence** (pdfplumber, 100% character accuracy).
Scanned PDFs and images give **medium confidence** (Tesseract OCR, occasional accent drops).

## Dashboard sections

| # | Section | What it shows |
|---|---------|---------------|
| — | **KPI cards** | Total spend · latest month with MoM% · YoY change · rolling avg · highest bill |
| 1 | Monthly Trend | Line + area chart with 3-month rolling average overlay |
| 2 | MoM & YoY % | Bar charts + full change table with € and % deltas per month |
| 3 | Type Breakdown | Stacked bar + donut showing share of each utility category |
| 4 | Seasonal Patterns | Average bill by calendar month + 4-season radar profile |
| 5 | Annual Comparison | Year-over-year spend by category |
| 6 | Top Providers | Horizontal bar ranking suppliers by total spend |
| 7 | Per-Utility Trends | One line per utility type — spot individual spikes |
| 8 | Summary Statistics | Min/max/avg/consumption per utility type |
| 9 | Unit Price Trends | €/kWh, €/m², €/m³ over time — isolates tariff changes from usage |
| 10 | Line-Item Cost by Month | Stacked bars of every individual charge |
| 11 | Price vs Consumption Decomposition | price_effect vs vol_effect per line item per month |
| 12 | Month-vs-Month Comparison | Side-by-side table of two recent months with deltas |

## Estonian translation coverage

Glossary (`backend/translation.py`) includes:

- **180+ utility terms** — Elektrienergia, Võrgutasu, Aktsiis, Taastuvenergia tasu, Käibemaks, Kuupäev, Tähtaeg, Viitenumber, Neto pind, Tasumisele kuulub, …
- **Housing association (korteriühistu) vocabulary** — Haldusteenus, Raamatupidamisteenus, Tehnosüsteemide hooldusteenus, Sise-ja väliskoristus, Porivaiba renditeenus, Prügivedu, Üldelekter, Üldvesi, Küte, Vee soojendamine, Remondifond
- **Months + abbreviations + OCR variants** — Jaanuar/Jaan, Veebruar/Veeb, Märts/Marts, Aprill/Apr, …
- **Weekdays** — full names (Esmaspäev → Monday) and single-letter forms (E, T, K, N, R, L, P)
- **Known providers** — Eesti Energia, Elektrilevi, Elering, Eesti Gaas, Tallinna Vesi, Gasum, Telia, Elisa, Tele2, Adven, Utilitas, Ragn-Sells, …

## Directory layout

```
backend/
├── main.py              FastAPI app, SQLite schema, analytics endpoint
├── parser.py            Tesseract OCR + pdfplumber + regex + column detector
├── translation.py       180-term Estonian→English glossary + period parser
├── seed_demo.py         Seed 3 sample bills without any API call
├── render_preview.py    ASCII preview of the dashboard
├── test_parser.py       End-to-end test on synthetic PNG
├── test_december.py     Validation on the December 2025 bill format
└── test_pdf.py          Validation on native-text PDFs
frontend/
└── src/
    ├── App.tsx
    ├── api.ts
    └── components/
        ├── UploadTab.tsx       Drag-and-drop upload + extraction result
        ├── BillsTab.tsx        List/edit/delete bills, per-bill detail view
        └── AnalyticsTab.tsx    12-section dashboard + Download PDF button
```

## PDF export

The "Download PDF" button in the Analytics header captures the whole dashboard via **html2canvas** and serialises it through **jsPDF** into a multi-page A4 document. Fully client-side — works offline once the dashboard is loaded.

Filename: `utility-bills-dashboard-YYYY-MM-DD.pdf`

## License

Public domain (repo is a demo).

Tesseract is Apache-2.0. pdfplumber, html2canvas and jsPDF are MIT-licensed.
