# Estonia Utility Bill Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Node 18+](https://img.shields.io/badge/node-18%2B-green)

Upload any invoice or bill (image or PDF), get it parsed into structured line items, and explore spending patterns through a 12-section analytics dashboard.

Three extraction backends are available:
- **Local OCR** *(default)* — Tesseract + `pdfplumber`, optimized for Estonian utility bills. Runs entirely locally, no API key required.
- **Free AI via OpenRouter** *(recommended for non-Estonian or unusual invoices)* — pick any free vision model (Gemini, Gemma, Llama, Qwen…) per upload. Requires a free OpenRouter key. Set `PARSER_BACKEND=openrouter`.
- **Claude API** *(premium alternative)* — highest accuracy, paid. Set `PARSER_BACKEND=claude`.

## Features

- **Three extraction backends** — local OCR for Estonian utility bills, free AI (OpenRouter) for anything else (rent, subscriptions, services, non-Estonian invoices, scanned docs with unusual layouts), Claude API as a premium option
- **Per-upload model picker** — the UI fetches OpenRouter's live list of free vision models, the user picks one at upload time, and the backend auto-falls-back through up to 4 models if the first one is delisted or rate-limited
- **Automatic quality detection** — if the local OCR can't read the invoice, the UI shows a warning banner directing the user to switch to an AI model
- **Open-source OCR pipeline**: Tesseract for images, `pdfplumber` for native-text PDFs, `pdf2image` + OCR fallback for scanned PDFs
- **Hardcoded Estonian→English dictionary** (~180 terms) — no API call needed for translation when using the local backend
  - Utility services: electricity, gas, water, heating, telecom, waste
  - Korteriühistu line items: Haldusteenus, Küte, Remondifond, Tehnosüsteemide hooldusteenus…
  - Months (Jaanuar → January), weekdays, units, invoice field labels
  - Inline meter-reading format: `Alg: 9644 Löpp: 9726` → `[Start: 9644, End: 9726]`
- **12-section analytics dashboard** with trends, MoM/YoY %, unit-price tracking, price-vs-consumption decomposition
- **One-click PDF export** of the whole dashboard (client-side, no server round-trip) — paginates at chart boundaries so charts are never split mid-body
- **Optional shared-password login** gate for deployed instances (disabled by default for local dev)

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

## Run with Docker (easiest)

```bash
# Tesseract backend (default):
docker compose up --build

# Free AI via OpenRouter (recommended for non-Estonian invoices):
OPENROUTER_API_KEY=sk-or-v1-... PARSER_BACKEND=openrouter docker compose up --build

# Claude backend (paid):
ANTHROPIC_API_KEY=sk-ant-... PARSER_BACKEND=claude docker compose up --build
```

> 💡 Get a free OpenRouter key at https://openrouter.ai/keys — no credit card required. It unlocks every `:free` vision model (Gemini 2.0 Flash, Gemma 3, Llama 3.2 Vision, Qwen-VL, etc.).

Open **http://localhost:5173**. Uploads and the SQLite DB are persisted in a named volume (`backend-data`).

## Deploy (free tier)

A free-tier cloud setup: **Vercel** for the frontend, **Render** for the backend.

> ⚠️ The demo uses a **single shared password** — fine for a personal deployment but not a real multi-user product. Treat it as a personal demo, not a shared service. For a public-grade deployment, swap this for proper OAuth or Cloudflare Access.

### 1. Backend on Render

1. Log in to [Render](https://render.com) → **New** → **Web Service** → pick this repo.
2. Settings:
   - **Root Directory**: `backend`
   - **Environment**: `Docker` (uses `backend/Dockerfile`)
   - **Instance Type**: `Free`
3. Add environment variables:
   - `PARSER_BACKEND` = `openrouter`
   - `OPENROUTER_API_KEY` = your key from https://openrouter.ai/keys
   - `OPENROUTER_MODEL` = `google/gemini-2.0-flash-exp:free` *(optional; overridable per upload)*
   - `APP_PASSWORD` = any password you'll type at the login screen
   - `AUTH_SECRET` = a long random hex string — generate locally with:
     ```
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
4. Click **Create Web Service**. First build takes ~5 min. Copy the generated URL (e.g. `https://ee-utility-trackly.onrender.com`).

The free tier spins down after 15 minutes of inactivity. The first request after a cold start takes ~30 s. The SQLite DB lives on the ephemeral disk and resets on every redeploy — for persistence, migrate to Supabase Postgres.

### 2. Frontend on Vercel

1. Log in to [Vercel](https://vercel.com) → **Add New** → **Project** → import this repo.
2. Settings:
   - **Root Directory**: `frontend`
   - **Framework**: `Vite` *(auto-detected)*
3. Environment variable:
   - `VITE_API_URL` = the Render URL from step 1 (no trailing slash)
4. Click **Deploy**. Your app is live at `https://<project>.vercel.app`.

The bundled `frontend/vercel.json` provides SPA routing so deep links / refreshes don't 404.

### 3. CORS

The backend accepts requests from `*.vercel.app` by default. For a custom domain, set `CORS_ALLOW_ORIGINS` on the Render service:
```
CORS_ALLOW_ORIGINS=https://bills.example.com,https://www.bills.example.com
```

### 4. Login

Visiting the Vercel URL will show a password prompt. Enter the `APP_PASSWORD` you set on Render. The token is stored in `localStorage` and lasts 7 days (override with `TOKEN_TTL_SEC`). To rotate the password, change `APP_PASSWORD` on Render — existing tokens stay valid until they expire unless you also rotate `AUTH_SECRET` (which invalidates every token immediately).

For local development, leave `APP_PASSWORD` unset and the login screen is skipped entirely.

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
./venv/bin/pip install -r requirements.txt

# Optional — seed 3 demo bills so the dashboard is populated immediately
./venv/bin/python seed_demo.py

# Run the API server (leave this terminal open)
./venv/bin/uvicorn main:app --port 8000
```

Backend is now at **http://localhost:8000**.

Backend env vars (see `backend/.env.example` for the full list):
- `PARSER_BACKEND=tesseract` *(default)* — open-source, local, no API key. Best on Estonian utility bills and korteriühistu invoices.
- `PARSER_BACKEND=openrouter` — free AI vision models via OpenRouter, requires `OPENROUTER_API_KEY` (free, no credit card). Works on any invoice format, any language, any layout — use this if the Tesseract parser shows a low-quality warning. Optionally set `OPENROUTER_MODEL` (any `:free` vision model ID) as the default; users can still override it per upload in the UI.
- `PARSER_BACKEND=claude` — Anthropic Claude API, requires `ANTHROPIC_API_KEY` (paid). Highest accuracy; use only if the free OpenRouter models aren't getting the job done.
- `APP_PASSWORD` — optional shared-password login gate. Unset = no login required.
- `AUTH_SECRET` — required when `APP_PASSWORD` is set. 64-char hex, generate with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `MAX_UPLOAD_BYTES` — hard cap on upload size in bytes (default 20 MB).
- `DB_PATH`, `UPLOADS_DIR`, `LOG_LEVEL` — override storage paths and log verbosity.

Frontend env var (see `frontend/.env.example`):
- `VITE_API_URL` — base URL of the backend. Defaults to `http://localhost:8000`.

> ⚠️ **Security**: for local development the API has no authentication. For deployed instances, set `APP_PASSWORD` + `AUTH_SECRET` to enable the built-in shared-password login screen (see **Deploy** section above). For multi-user production, swap for proper OAuth or Cloudflare Access.

### 4. Start the frontend (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. You'll see three tabs: **Upload**, **Bills**, **Analytics**.

### 5. Try it

1. Go to **Upload** → pick an extraction method (🔍 Local OCR or 🤖 AI / OpenRouter) and drag in your invoice. The local parser handles Estonian utility bills out of the box; for any other format, switch to the AI tab and pick any free vision model from the dropdown.
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
./venv/bin/pip install --index-url https://pypi.org/simple/ -r requirements.txt
```

**`Failed to fetch` / CORS error in browser**
The backend must be on port 8000 — the frontend is hardcoded to that URL in `frontend/src/api.ts`. If you change the port, update `BASE` there too.

**Port already in use (`[Errno 48] Address already in use`)**
Something else is on port 8000. Either kill it (`lsof -ti:8000 | xargs kill`) or change the port: `./venv/bin/uvicorn main:app --port 8001` + update `BASE` in `frontend/src/api.ts`.

**Dashboard shows no data**
Either no bills uploaded yet, or the backend isn't running. Check the **Upload** tab works, or run `python seed_demo.py` to load three sample bills.

**Amber "OCR couldn't read this invoice" warning**
The local Tesseract parser couldn't extract enough data — typically means the invoice is non-Estonian, has an unusual layout, or is a low-quality scan. Switch the **Extraction method** toggle on the Upload tab to **🤖 AI (OpenRouter)** and re-upload — no restart needed. Requires `OPENROUTER_API_KEY` to be set (free key at https://openrouter.ai/keys).

**Amber "File saved, but data couldn't be extracted" after AI upload**
The selected OpenRouter model failed (rate-limited, delisted from the free tier, or returned a non-JSON response). The error text in the banner tells you which. Pick a different model from the dropdown and try again — the backend auto-falls-back through up to 4 free models, so transient failures usually resolve on the next attempt.

**`RuntimeError: OPENROUTER_API_KEY must be set for the openrouter parser`**
The backend can't see your OpenRouter key. For local dev, copy `backend/.env.example` to `backend/.env` and fill in `OPENROUTER_API_KEY=sk-or-v1-...` — then restart `uvicorn`. For deployed instances, add the env var in Render's dashboard and wait for the automatic redeploy.

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
For non-Estonian or non-standard invoices, switch to the **AI (OpenRouter)** backend — free vision models typically match Claude's accuracy on invoices they're given.

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
├── parser_openrouter.py OpenRouter client + auto-fallback chain across free vision models
├── auth.py              Shared-password login (HMAC-signed tokens, stdlib only)
├── translation.py       180-term Estonian→English glossary + period parser
├── seed_demo.py         Seed 3 sample bills without any API call
├── render_preview.py    ASCII preview of the dashboard
├── test_auth.py         Unit tests for token roundtrip, tampering, expiry
├── test_claude_parser.py  Unit tests for the Claude parser branch
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
