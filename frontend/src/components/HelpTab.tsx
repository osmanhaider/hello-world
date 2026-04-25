import { Upload, Receipt, BarChart2, FileText, RefreshCw, Download, ShieldCheck, Terminal } from "lucide-react";

const cardStyle: React.CSSProperties = {
  background: "var(--surface-1)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: 24,
};

const sectionTitleStyle: React.CSSProperties = {
  color: "var(--text-1)",
  fontSize: 16,
  fontWeight: 600,
  margin: "32px 0 16px",
};

const subtleChip: React.CSSProperties = {
  display: "inline-block",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  padding: "3px 10px",
  fontSize: 12,
  color: "var(--text-1)",
  marginRight: 6,
  marginBottom: 6,
};

// Steps shown in the quickstart
const STEPS: { icon: React.ElementType; title: string; body: string }[] = [
  {
    icon: Upload,
    title: "1 · Upload your bill",
    body: "Drop a PDF or photo of your Estonian utility bill on the Upload tab. Tesseract OCR and pdfplumber extract every line item locally — no API key or external service needed.",
  },
  {
    icon: Receipt,
    title: "2 · Review the extracted details",
    body: "Switch to the Bills tab to see provider, period, totals and each translated line item. Edit any mis-parsed field in place or delete bills you don't want to keep.",
  },
  {
    icon: BarChart2,
    title: "3 · Explore the analytics",
    body: "Open the Analytics tab for 12 dashboard sections: MoM/YoY change, unit-price trends, price vs consumption decomposition, per-utility line charts and more.",
  },
];

// Dashboard sections — numbers match Analytics tab
const DASHBOARD_SECTIONS: [string, string][] = [
  ["KPI cards", "Total spend · latest month with MoM% · YoY change · rolling 3-month average · highest single bill"],
  ["1. Monthly Trend", "Line + area chart with 3-month rolling average overlay"],
  ["2. MoM & YoY %", "Bar charts + full change table with € and % deltas per month"],
  ["3. Type Breakdown", "Stacked bar + donut showing share of each utility category"],
  ["4. Seasonal Patterns", "Average bill by calendar month + 4-season radar profile"],
  ["5. Annual Comparison", "Year-over-year spend by category"],
  ["6. Top Providers", "Horizontal bar ranking suppliers by total spend"],
  ["7. Per-Utility Trends", "One line per utility type — spot individual spikes"],
  ["8. Summary Statistics", "Min/max/avg/consumption per utility type"],
  ["9. Unit Price Trends", "€/kWh, €/m², €/m³ over time — isolates tariff changes from usage"],
  ["10. Line-Item Cost by Month", "Stacked bars of every individual charge"],
  ["11. Price vs Consumption Decomposition", "Price effect vs volume effect per line item per month"],
  ["12. Month-vs-Month Comparison", "Side-by-side table of two recent months with deltas"],
];

// Curated glossary grouped by theme — full 180+ term dictionary lives
// in the backend (translation.py) and is applied automatically.
const GLOSSARY_GROUPS: { title: string; rows: [string, string][] }[] = [
  {
    title: "Housing association (korteriühistu)",
    rows: [
      ["Haldusteenus", "Building management service"],
      ["Raamatupidamisteenus", "Accounting service"],
      ["Tehnosüsteemide hooldusteenus", "Technical systems maintenance"],
      ["Sise- ja väliskoristus", "Interior & exterior cleaning"],
      ["Porivaiba renditeenus", "Doormat rental service"],
      ["Remondifond", "Repair / renovation fund"],
      ["Üldelekter", "Common area electricity"],
      ["Üldvesi", "Common area water"],
      ["Küte", "Heating"],
      ["Vee soojendamine", "Water heating"],
    ],
  },
  {
    title: "Electricity",
    rows: [
      ["Elektrienergia", "Electricity"],
      ["Elekter päevane / öine", "Electricity (daytime / night-time)"],
      ["Võrgutasu / Võrguteenus", "Grid fee / service"],
      ["Aktsiis", "Excise duty"],
      ["Taastuvenergia tasu", "Renewable energy fee"],
      ["Energiatõhususe tasu", "Energy efficiency fee"],
      ["Käibemaks (KM)", "VAT"],
    ],
  },
  {
    title: "Water, heating & gas",
    rows: [
      ["Külm vesi / Soe vesi", "Cold water / Hot water"],
      ["Kanalisatsioon", "Sewerage / wastewater"],
      ["Kaugküte", "District heating"],
      ["Soojusenergia", "Thermal energy"],
      ["Maagaas", "Natural gas"],
    ],
  },
  {
    title: "Invoice fields",
    rows: [
      ["Arve nr.", "Invoice no."],
      ["Kuupäev", "Date"],
      ["Tähtaeg", "Due date"],
      ["Viitenumber", "Reference number"],
      ["Periood", "Period"],
      ["Tasumisele kuulub", "Amount due"],
      ["Kokku", "Total"],
      ["Neto pind", "Net floor area"],
      ["Alg: … Löpp: …", "Start (opening meter) … End (closing meter)"],
    ],
  },
];

const KPI_NOTES: [string, string][] = [
  ["Total Spend", "Sum of every uploaded invoice total (not line items) — uses data.totals.total_eur."],
  ["Latest Month + MoM", "Most recent month grouped by billing period (period_start). Green % = cheaper."],
  ["YoY Change", "Compares same calendar month in prior year, when available."],
  ["Highest Single Bill", "Largest single invoice total across the whole history."],
];

const TIPS: [string, string][] = [
  ["Use PDF when possible", "Native-text PDFs give 100% extraction confidence; images fall back to OCR (~95%)."],
  ["Upload the same bill twice", "The app detects duplicates (same filename, or same provider + period) and replaces the previous entry automatically — you'll see an amber 'Existing bill replaced' banner."],
  ["Period-based grouping", "Analytics group by billing period, not invoice issue date. A March bill issued April 13 still counts as March."],
  ["Works offline after install", "Once dependencies are installed, the app runs entirely on localhost — no cloud round-trips."],
];

export default function HelpTab() {
  return (
    <div style={{ maxWidth: 920, margin: "0 auto" }}>
      <h2 style={{ color: "var(--text-1)", fontSize: 22, margin: "0 0 8px", letterSpacing: -0.2 }}>How to use this app</h2>
      <p style={{ color: "var(--text-2)", fontSize: 14, margin: "0 0 24px" }}>
        Upload monthly utility bills, let the open-source parser extract every line item in
        Estonian, and explore spend patterns through 12 analytics sections. Everything runs
        locally — no API key required.
      </p>

      {/* Quickstart */}
      <div className="list-stagger" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        {STEPS.map(({ icon: Icon, title, body }, i) => (
          <div
            key={title}
            className="lift"
            style={{ ...cardStyle, ["--i" as string]: i } as React.CSSProperties}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: "var(--accent-soft)", border: "1px solid var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "var(--accent)",
              }}>
                <Icon size={16} />
              </div>
              <div style={{ color: "var(--text-1)", fontWeight: 600, fontSize: 14 }}>{title}</div>
            </div>
            <div style={{ color: "var(--text-2)", fontSize: 13, lineHeight: 1.55 }}>{body}</div>
          </div>
        ))}
      </div>

      {/* Tips */}
      <div style={sectionTitleStyle}>💡 Tips for best results</div>
      <div style={cardStyle}>
        {TIPS.map(([t, d], i) => (
          <div key={t} style={{
            display: "grid",
            gridTemplateColumns: "180px 1fr",
            gap: 16,
            padding: "10px 0",
            borderBottom: i < TIPS.length - 1 ? "1px solid var(--divider)" : "none",
          }}>
            <div style={{ color: "var(--text-1)", fontWeight: 500, fontSize: 13 }}>{t}</div>
            <div style={{ color: "var(--text-2)", fontSize: 13, lineHeight: 1.5 }}>{d}</div>
          </div>
        ))}
      </div>

      {/* KPI cheat-sheet */}
      <div style={sectionTitleStyle}>📌 KPI cheat-sheet</div>
      <div style={cardStyle}>
        {KPI_NOTES.map(([t, d], i) => (
          <div key={t} style={{
            display: "grid",
            gridTemplateColumns: "180px 1fr",
            gap: 16,
            padding: "10px 0",
            borderBottom: i < KPI_NOTES.length - 1 ? "1px solid var(--divider)" : "none",
          }}>
            <div style={{ color: "var(--text-1)", fontWeight: 500, fontSize: 13 }}>{t}</div>
            <div style={{ color: "var(--text-2)", fontSize: 13, lineHeight: 1.5 }}>{d}</div>
          </div>
        ))}
      </div>

      {/* Dashboard overview */}
      <div style={sectionTitleStyle}>📊 Dashboard sections</div>
      <div style={cardStyle}>
        {DASHBOARD_SECTIONS.map(([t, d], i) => (
          <div key={t} style={{
            display: "grid",
            gridTemplateColumns: "220px 1fr",
            gap: 16,
            padding: "9px 0",
            borderBottom: i < DASHBOARD_SECTIONS.length - 1 ? "1px solid var(--divider)" : "none",
          }}>
            <div style={{ color: "var(--text-1)", fontWeight: 500, fontSize: 13 }}>{t}</div>
            <div style={{ color: "var(--text-2)", fontSize: 13, lineHeight: 1.5 }}>{d}</div>
          </div>
        ))}
      </div>

      {/* Glossary */}
      <div style={sectionTitleStyle}>📖 Estonian → English glossary</div>
      <p style={{ color: "var(--text-3)", fontSize: 12, margin: "0 0 12px" }}>
        Most common terms used on Estonian utility bills. The backend dictionary covers 180+ terms
        and is applied automatically when you upload.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
        {GLOSSARY_GROUPS.map(group => (
          <div key={group.title} className="lift" style={cardStyle}>
            <div style={{
              fontSize: 11, color: "var(--accent)", textTransform: "uppercase",
              letterSpacing: "0.05em", fontWeight: 600, marginBottom: 10,
            }}>{group.title}</div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <tbody>
                {group.rows.map(([et, en], i) => (
                  <tr key={et} style={{ borderBottom: i < group.rows.length - 1 ? "1px solid var(--divider)" : "none" }}>
                    <td style={{ padding: "7px 0", color: "var(--text-2)", width: "45%" }}>{et}</td>
                    <td style={{ padding: "7px 0", color: "var(--text-1)" }}>{en}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {/* Feature chips */}
      <div style={sectionTitleStyle}>✨ What this app does</div>
      <div className="lift" style={cardStyle}>
        <div style={{ display: "flex", flexWrap: "wrap" }}>
          <span style={subtleChip}><FileText size={12} style={{ verticalAlign: -1, marginRight: 4 }} />OCR + native PDF parsing</span>
          <span style={subtleChip}>Local translation (180+ terms)</span>
          <span style={subtleChip}>Korteriühistu line-item split</span>
          <span style={subtleChip}><RefreshCw size={12} style={{ verticalAlign: -1, marginRight: 4 }} />Duplicate detection & replace</span>
          <span style={subtleChip}>12-section dashboard</span>
          <span style={subtleChip}><Download size={12} style={{ verticalAlign: -1, marginRight: 4 }} />Client-side PDF export</span>
          <span style={subtleChip}><ShieldCheck size={12} style={{ verticalAlign: -1, marginRight: 4 }} />No API key required</span>
          <span style={subtleChip}><Terminal size={12} style={{ verticalAlign: -1, marginRight: 4 }} />FastAPI + React + SQLite</span>
        </div>
      </div>

      <div style={{ height: 40 }} />
    </div>
  );
}
