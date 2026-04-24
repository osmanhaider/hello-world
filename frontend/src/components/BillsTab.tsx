import { useEffect, useState } from "react";
import { api, type Bill } from "../api";
import { Trash2, ChevronDown, ChevronUp, AlertCircle, Loader2 } from "lucide-react";
import { useIsMobile } from "../hooks/useIsMobile";

const UTILITY_ICONS: Record<string, string> = {
  electricity: "⚡", gas: "🔥", water: "💧",
  heating: "♨️", internet: "🌐", waste: "🗑️", other: "📄",
};

const TYPE_COLORS: Record<string, string> = {
  electricity: "#f59e0b", gas: "#f97316", water: "#3b82f6",
  heating: "#ef4444", internet: "#8b5cf6", waste: "#6b7280", other: "#9ca3af",
};

export default function BillsTab() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [sortKey, setSortKey] = useState<"bill_date" | "amount_eur" | "utility_type">("bill_date");

  useEffect(() => {
    api.listBills().then(r => { setBills(r.data); setLoading(false); });
  }, []);

  const deleteBill = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this bill?")) return;
    await api.deleteBill(id);
    setBills(bs => bs.filter(b => b.id !== id));
  };

  const types = ["all", ...Array.from(new Set(bills.map(b => b.utility_type).filter(Boolean) as string[]))];
  const filtered = bills
    .filter(b => filter === "all" || b.utility_type === filter)
    .sort((a, b) => {
      if (sortKey === "amount_eur") return (b.amount_eur ?? 0) - (a.amount_eur ?? 0);
      if (sortKey === "utility_type") return (a.utility_type ?? "").localeCompare(b.utility_type ?? "");
      return (b.bill_date ?? b.upload_date).localeCompare(a.bill_date ?? a.upload_date);
    });

  const totalEur = filtered.reduce((s, b) => s + (b.amount_eur ?? 0), 0);

  const isMobile = useIsMobile();
  const cardStyle = { background: "#1a1d27", borderRadius: 12, border: "1px solid #2d3148" };
  const inputStyle = { background: "#252838", border: "1px solid #374151", borderRadius: 6, color: "#e5e7eb", padding: "6px 10px", fontSize: 13 };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200, gap: 12, color: "#9ca3af" }}>
      <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} /> Loading bills…
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (!bills.length) return (
    <div style={{ textAlign: "center", padding: 80, color: "#6b7280" }}>
      <AlertCircle size={40} style={{ marginBottom: 12 }} />
      <p>No bills yet. Upload your first utility bill!</p>
    </div>
  );

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ color: "white", margin: 0, fontSize: 22 }}>Bill History</h2>
          <p style={{ color: "#9ca3af", margin: "4px 0 0", fontSize: 13 }}>
            {filtered.length} bill{filtered.length !== 1 ? "s" : ""} · Total: <strong style={{ color: "#22c55e" }}>€{totalEur.toFixed(2)}</strong>
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={filter} onChange={e => setFilter(e.target.value)} style={inputStyle}>
            {types.map(t => <option key={t} value={t}>{t === "all" ? "All types" : `${UTILITY_ICONS[t] || ""} ${t}`}</option>)}
          </select>
          <select value={sortKey} onChange={e => setSortKey(e.target.value as typeof sortKey)} style={inputStyle}>
            <option value="bill_date">Sort: Date</option>
            <option value="amount_eur">Sort: Amount</option>
            <option value="utility_type">Sort: Type</option>
          </select>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {filtered.map(bill => {
          const isOpen = expanded === bill.id;
          const color = TYPE_COLORS[bill.utility_type ?? "other"] ?? "#9ca3af";
          const raw = bill.raw_json ? JSON.parse(bill.raw_json) : {};

          return (
            <div key={bill.id} style={{ ...cardStyle, overflow: "hidden" }}>
              <div
                onClick={() => setExpanded(isOpen ? null : bill.id)}
                style={{ padding: isMobile ? "12px 14px" : "16px 20px", cursor: "pointer", display: "flex", alignItems: "center", gap: isMobile ? 10 : 16 }}
              >
                <div style={{ width: 36, height: 36, borderRadius: 8, background: `${color}22`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>
                  {UTILITY_ICONS[bill.utility_type ?? "other"] ?? "📄"}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, color: "white", fontSize: isMobile ? 14 : 15 }}>{bill.provider ?? "Unknown Provider"}</span>
                    {bill.utility_type && !isMobile && (
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, background: `${color}22`, color, border: `1px solid ${color}44`, textTransform: "capitalize" }}>
                        {bill.utility_type}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 2 }}>
                    {bill.bill_date ?? bill.upload_date?.slice(0, 10)}
                    {bill.period_start && bill.period_end && !isMobile && ` · ${bill.period_start} → ${bill.period_end}`}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: isMobile ? 15 : 18, color: "#22c55e" }}>
                    {bill.amount_eur != null ? `€${bill.amount_eur.toFixed(2)}` : "—"}
                  </div>
                  {bill.consumption_kwh != null && !isMobile && <div style={{ fontSize: 12, color: "#9ca3af" }}>{bill.consumption_kwh} kWh</div>}
                  {bill.consumption_m3 != null && !isMobile && <div style={{ fontSize: 12, color: "#9ca3af" }}>{bill.consumption_m3} m³</div>}
                </div>
                <button onClick={e => deleteBill(bill.id, e)} style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", padding: 4, borderRadius: 4, flexShrink: 0 }}>
                  <Trash2 size={15} />
                </button>
                {isOpen ? <ChevronUp size={15} color="#6b7280" style={{ flexShrink: 0 }} /> : <ChevronDown size={15} color="#6b7280" style={{ flexShrink: 0 }} />}
              </div>

              {isOpen && (
                <div style={{ borderTop: "1px solid #2d3148", padding: "16px 20px" }}>
                  {raw.translated_summary && (
                    <div style={{ marginBottom: 16, padding: "12px 14px", background: "#1e2640", borderLeft: "3px solid #2563eb", borderRadius: 6 }}>
                      <div style={{ fontSize: 11, color: "#2563eb", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4, fontWeight: 600 }}>
                        🌍 English Summary
                      </div>
                      <div style={{ fontSize: 13, color: "#e5e7eb", lineHeight: 1.5 }}>{raw.translated_summary}</div>
                    </div>
                  )}

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "12px 24px" }}>
                    {[
                      ["Account #", bill.account_number],
                      ["Address", bill.address],
                      ["Filename", bill.filename],
                      ["Uploaded", bill.upload_date?.slice(0, 10)],
                      ["Due Date", raw.due_date],
                      ["Period (EN)", raw.period_en ?? raw.period],
                      ["VAT", raw.vat_amount != null ? `€${raw.vat_amount}` : null],
                      ["Without VAT", raw.amount_without_vat != null ? `€${raw.amount_without_vat}` : null],
                      ["Meter Start", raw.meter_reading_start],
                      ["Meter End", raw.meter_reading_end],
                      ["Confidence", raw.confidence],
                    ].map(([label, val]) => val ? (
                      <div key={label as string}>
                        <div style={{ fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
                        <div style={{ fontSize: 13, color: "#d1d5db", marginTop: 2, wordBreak: "break-all" }}>{val as string}</div>
                      </div>
                    ) : null)}
                  </div>

                  {Array.isArray(raw.line_items) && raw.line_items.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8, fontWeight: 600 }}>
                        Line Items (Estonian → English)
                      </div>
                      <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 360 }}>
                        <thead>
                          <tr style={{ borderBottom: "1px solid #2d3148" }}>
                            <th style={{ padding: "6px 0", textAlign: "left", color: "#6b7280", fontSize: 11, fontWeight: 600 }}>ESTONIAN</th>
                            <th style={{ padding: "6px 0", textAlign: "left", color: "#6b7280", fontSize: 11, fontWeight: 600 }}>ENGLISH</th>
                            <th style={{ padding: "6px 0", textAlign: "right", color: "#6b7280", fontSize: 11, fontWeight: 600 }}>AMOUNT</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(raw.line_items as Array<Record<string, unknown>>).map((li, i) => (
                            <tr key={i} style={{ borderBottom: "1px solid #1e2132" }}>
                              <td style={{ padding: "6px 8px 6px 0", color: "#9ca3af" }}>{String(li.description_et ?? "—")}</td>
                              <td style={{ padding: "6px 0", color: "#e5e7eb" }}>{String(li.description_en ?? "—")}</td>
                              <td style={{ padding: "6px 0", textAlign: "right", color: "#22c55e", fontVariantNumeric: "tabular-nums" }}>
                                {li.amount_eur != null ? `€${(li.amount_eur as number).toFixed(2)}` : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      </div>
                    </div>
                  )}

                  {raw.glossary && typeof raw.glossary === "object" && Object.keys(raw.glossary).length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8, fontWeight: 600 }}>
                        📖 Glossary
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 6 }}>
                        {Object.entries(raw.glossary as Record<string, string>).map(([et, en]) => (
                          <div key={et} style={{ background: "#252838", padding: "6px 10px", borderRadius: 6, fontSize: 12 }}>
                            <span style={{ color: "#9ca3af" }}>{et}</span>
                            <span style={{ color: "#6b7280", margin: "0 6px" }}>→</span>
                            <span style={{ color: "#e5e7eb" }}>{en}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {bill.notes && (
                    <div style={{ marginTop: 12, padding: "10px 14px", background: "#252838", borderRadius: 6, fontSize: 13, color: "#9ca3af" }}>
                      {bill.notes}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
