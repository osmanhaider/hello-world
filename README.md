# Estonia Utility Bill Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Node 18+](https://img.shields.io/badge/node-18%2B-green)

Upload any invoice or bill (image or PDF), get it parsed into structured line items, and explore spending patterns through a 12-section analytics dashboard.

Two extraction backends are available:
- **Local OCR** *(default)* — Tesseract + `pdfplumber`, optimized for Estonian utility bills. Runs entirely locally, no API key required.
- **Claude API** *(optional)* — handles any invoice type, any language, any layout. Set `PARSER_BACKEND=claude`.

## Features

- **Two extraction backends** — local OCR for Estonian utility bills, Claude API for anything else (rent, subscriptions, services, non-Estonian invoices, scanned docs with unusual layouts)
- **Automatic quality detection** — if the local OCR can't read the invoice, the UI shows a warning banner directing the user to switch to the Claude backend
- **Open-source OCR pipeline**: Tesseract for images, `pdfplumber` for native-text PDFs, `pdf2image` + OCR fallback for scanned PDFs
- **Hardcoded Estonian→English dictionary** (~180 terms) — no API call needed for translation when using the local backend
  - Utility services: electricity, gas, water, heating, telecom, waste
  - Korteriühistu line items: Haldusteenus, Küte, Remondifond, Tehnosüsteemide hooldusteenus…
  - Months (Jaanuar → January), weekdays, units, invoice field labels
  - Inline meter-reading format: `Alg: 9644 Löpp: 9726` → `[Start: 9644, End: 9726]`
- **12-section analytics dashboard** with trends, MoM/YoY %, unit-price tracking, price-vs-consumption decomposition
- **One-click PDF export** of the whole dashboard (client-side, no server round-trip) — paginates at chart boundaries so charts are never split mid-body

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

## Run locally

### Prerequisites

You need **Python 3.10+** and **Node.js 18+**. Verify with:
```bash
python3 --version
node --version
```

### 1. Clone the repo

```bash
git clone https://github.com/osmanhaider/ee-utility-trackly.git
cd ee-utility-trackly
```

### 2. Install system dependencies

Pick the block for your OS — this installs Tesseract (OCR engine), the **Estonian** language pack, and poppler (PDF rasteriser):

<details>
<summary><strong>macOS (Homebrew)</strong></summary>

```bash
brew install tesseract tesseract-lang poppler
```
`tesseract-lang` bundles the Estonian training data. Verify with `tesseract --list-langs` — you should see `est` in the output.
</details>

<details>
<summary><strong>Ubuntu / Debian</strong></summary>

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-est tesseract-ocr-eng \
                        poppler-utils
```
</details>

<details>
<summary><strong>Fedora / RHEL</strong></summary>

```bash
sudo dnf install -y tesseract tesseract-langpack-est poppler-utils
```
</details>

Sanity check:
```bash
tesseract --list-langs        # must include 'est'
which pdftoppm                # must print a path
```

### 3. Start the backend

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn python-multipart anthropic aiosqlite \
                      pillow pdf2image pytesseract pdfplumber

# Optional — seed 3 demo bills so the dashboard is populated immediately
./venv/bin/python seed_demo.py

# Run the API server (leave this terminal open)
./venv/bin/uvicorn main:app --port 8000
```

Backend is now at **http://localhost:8000**.

Backend env vars:
- `PARSER_BACKEND=tesseract` *(default)* — open-source, local, no API key. Best on Estonian utility bills and korteriühistu invoices.
- `PARSER_BACKEND=claude` — Anthropic Claude API, requires `ANTHROPIC_API_KEY`. Works on any invoice format, any language, any layout — use this if the Tesseract parser shows a low-quality warning for your invoice.

### 4. Start the frontend (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. You'll see three tabs: **Upload**, **Bills**, **Analytics**.

### 5. Try it

1. Go to **Upload** → drag in a PDF or image of your invoice. The local parser handles Estonian utility bills out of the box; for any other format, an amber warning will suggest switching to the Claude backend.
2. Open the **Bills** tab to see everything stored with expandable per-bill details.
3. Open **Analytics** to explore 12 dashboard sections — click **Download PDF** to export.

## Troubleshooting

**`tesseract: command not found`**
Tesseract isn't installed. Re-run step 2 for your OS.

**`est.traineddata not found` / only `eng` listed**
The Estonian language pack is missing. On macOS: `brew install tesseract-lang`. On Ubuntu: `sudo apt-get install tesseract-ocr-est`.

**`pip install` fails with `401 Error, Credentials not correct`**
Your pip is pointing at a private corporate index (e.g. AWS CodeArtifact). Bypass it for this one command:
```bash
./venv/bin/pip install --index-url https://pypi.org/simple/ \
    fastapi uvicorn python-multipart anthropic aiosqlite \
    pillow pdf2image pytesseract pdfplumber
```

**`Failed to fetch` / CORS error in browser**
The backend must be on port 8000 — the frontend is hardcoded to that URL in `frontend/src/api.ts`. If you change the port, update `BASE` there too.

**Port already in use (`[Errno 48] Address already in use`)**
Something else is on port 8000. Either kill it (`lsof -ti:8000 | xargs kill`) or change the port: `./venv/bin/uvicorn main:app --port 8001` + update `BASE` in `frontend/src/api.ts`.

**Dashboard shows no data**
Either no bills uploaded yet, or the backend isn't running. Check the **Upload** tab works, or run `python seed_demo.py` to load three sample bills.

**Amber "OCR couldn't read this invoice" warning**
The local Tesseract parser couldn't extract enough data — typically means the invoice is non-Estonian, has an unusual layout, or is a low-quality scan. Restart the backend with `PARSER_BACKEND=claude ANTHROPIC_API_KEY=sk-ant-... ./venv/bin/uvicorn main:app --port 8000` and re-upload.

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

## Contributing

Bug reports, PRs and Estonian term additions are welcome. Fork, branch, send a pull request —
the codebase is small, tests live in `backend/test_*.py`, and the frontend type-checks with
`tsc --noEmit` and builds with `vite build`.

## License

[MIT](LICENSE) © 2026 Osman Haider.

Third-party components keep their own licenses: Tesseract is Apache-2.0; pdfplumber, pdf2image,
FastAPI, Recharts, html2canvas and jsPDF are MIT.
