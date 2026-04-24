import { useState, useCallback, useRef } from "react";
import { api } from "../api";
import { Upload, CheckCircle, AlertCircle, Loader2, RefreshCw } from "lucide-react";

const UTILITY_ICONS: Record<string, string> = {
  electricity: "⚡",
  gas: "🔥",
  water: "💧",
  heating: "♨️",
  internet: "🌐",
  waste: "🗑️",
  other: "📄",
};

interface UploadTabProps {
  onSuccess: () => void;
}

type Status = "idle" | "uploading" | "success" | "replaced" | "error";
type ParserMode = "tesseract" | "openrouter";

const FREE_MODELS = [
  { id: "google/gemini-2.0-flash-exp:free", label: "Gemini 2.0 Flash (best)" },
  { id: "meta-llama/llama-3.2-90b-vision-instruct:free", label: "Llama 3.2 90B Vision" },
  { id: "qwen/qwen2-vl-7b-instruct:free", label: "Qwen2-VL 7B" },
  { id: "microsoft/phi-3-vision-128k-instruct:free", label: "Phi-3 Vision" },
];

export default function UploadTab({ onSuccess }: UploadTabProps) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [parserMode, setParserMode] = useState<ParserMode>("openrouter");
  const [selectedModel, setSelectedModel] = useState(FREE_MODELS[0].id);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setStatus("uploading");
    setParsed(null);
    setErrorMsg("");
    try {
      const res = await api.uploadBill(
        file,
        parserMode,
        parserMode === "openrouter" ? selectedModel : undefined,
      );
      setParsed(res.data.parsed);
      setStatus(res.data.replaced ? "replaced" : "success");
      setTimeout(onSuccess, 2000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setErrorMsg(msg);
      setStatus("error");
    }
  }, [onSuccess, parserMode, selectedModel]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const cardStyle = {
    background: "#1a1d27",
    borderRadius: 12,
    border: "1px solid #2d3148",
    padding: 24,
  };

  const isSuccess = status === "success" || status === "replaced";

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ color: "white", marginBottom: 8, fontSize: 22 }}>Upload Invoice / Bill</h2>
      <p style={{ color: "#9ca3af", marginBottom: 16, fontSize: 14 }}>
        Choose how to extract data from your invoice, then drop or select the file.
      </p>

      {/* Parser selector */}
      <div style={{ ...cardStyle, marginBottom: 16, padding: 16 }}>
        <div style={{ fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10, fontWeight: 600 }}>
          Extraction method
        </div>
        <div style={{ display: "flex", gap: 8, marginBottom: parserMode === "openrouter" ? 12 : 0 }}>
          {([
            { id: "openrouter", label: "🤖 AI (OpenRouter)", desc: "Free vision models — any invoice, any language" },
            { id: "tesseract", label: "🔍 Local OCR", desc: "Offline, no API key — best for standard layouts" },
          ] as { id: ParserMode; label: string; desc: string }[]).map(({ id, label, desc }) => (
            <button
              key={id}
              onClick={() => setParserMode(id)}
              style={{
                flex: 1,
                background: parserMode === id ? "#1e2640" : "#252838",
                border: `1.5px solid ${parserMode === id ? "#2563eb" : "#374151"}`,
                borderRadius: 8,
                padding: "10px 12px",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <div style={{ color: parserMode === id ? "#93c5fd" : "#e5e7eb", fontSize: 13, fontWeight: 600 }}>{label}</div>
              <div style={{ color: "#6b7280", fontSize: 11, marginTop: 2 }}>{desc}</div>
            </button>
          ))}
        </div>

        {parserMode === "openrouter" && (
          <div>
            <label style={{ fontSize: 12, color: "#9ca3af", display: "block", marginBottom: 4 }}>Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                width: "100%",
                background: "#252838",
                border: "1px solid #374151",
                borderRadius: 6,
                color: "#e5e7eb",
                padding: "7px 10px",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {FREE_MODELS.map(m => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          ...cardStyle,
          border: `2px dashed ${dragging ? "#2563eb" : "#374151"}`,
          background: dragging ? "#1e2640" : "#1a1d27",
          textAlign: "center",
          padding: "48px 24px",
          cursor: "pointer",
          transition: "all 0.15s",
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          style={{ display: "none" }}
          onChange={onFileChange}
        />
        {status === "uploading" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <Loader2 size={40} color="#2563eb" style={{ animation: "spin 1s linear infinite" }} />
            <p style={{ color: "#9ca3af", margin: 0 }}>
              {parserMode === "openrouter" ? "Sending to AI model…" : "Running OCR & extracting line items…"}
            </p>
          </div>
        ) : status === "replaced" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <RefreshCw size={40} color="#f59e0b" />
            <p style={{ color: "#f59e0b", margin: 0, fontWeight: 600 }}>Existing bill replaced</p>
            <p style={{ color: "#9ca3af", margin: 0, fontSize: 13 }}>Duplicate detected — previous entry updated</p>
          </div>
        ) : status === "success" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <CheckCircle size={40} color="#22c55e" />
            <p style={{ color: "#22c55e", margin: 0, fontWeight: 600 }}>Bill uploaded successfully!</p>
            <p style={{ color: "#9ca3af", margin: 0, fontSize: 13 }}>Redirecting to bills list…</p>
          </div>
        ) : status === "error" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <AlertCircle size={40} color="#ef4444" />
            <p style={{ color: "#ef4444", margin: 0 }}>{errorMsg}</p>
            <p style={{ color: "#9ca3af", margin: 0, fontSize: 13 }}>Click to try again</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div style={{ width: 64, height: 64, background: "#1e2640", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Upload size={28} color="#2563eb" />
            </div>
            <div>
              <p style={{ color: "white", margin: 0, fontWeight: 600 }}>Drop your bill here</p>
              <p style={{ color: "#9ca3af", margin: "4px 0 0", fontSize: 13 }}>or click to browse — JPG, PNG, PDF supported</p>
            </div>
          </div>
        )}
      </div>

      {isSuccess && parsed && Boolean(parsed._low_quality) && (
        <div style={{
          ...cardStyle,
          marginTop: 24,
          borderLeft: "3px solid #f59e0b",
          background: "#1f1a0e",
          display: "flex",
          gap: 12,
          alignItems: "flex-start",
        }}>
          <AlertCircle size={20} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ color: "#f59e0b", fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
              OCR couldn't read this invoice
            </div>
            <div style={{ color: "#d1d5db", fontSize: 13, lineHeight: 1.5 }}>
              The local OCR parser found very little data — this usually means the invoice
              layout or language doesn't match the built-in patterns. Switch to{" "}
              <strong style={{ color: "#93c5fd" }}>AI (OpenRouter)</strong> above and re-upload
              for accurate extraction from any invoice format or language.
            </div>
          </div>
        </div>
      )}

      {isSuccess && parsed && (
        <>
          <div style={{ ...cardStyle, marginTop: 24 }}>
            <h3 style={{ color: "white", margin: "0 0 16px", fontSize: 16 }}>
              {UTILITY_ICONS[parsed.utility_type as string] || "📄"} Extracted Details
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px 24px" }}>
              {[
                ["Provider", parsed.provider],
                ["Type", parsed.utility_type],
                ["Amount", parsed.amount_eur != null ? `€${(parsed.amount_eur as number).toFixed(2)}` : null],
                ["Bill Date", parsed.bill_date],
                ["Period", parsed.period_en ?? (parsed.period_start && parsed.period_end ? `${parsed.period_start} → ${parsed.period_end}` : parsed.period)],
                ["Consumption", parsed.consumption_kwh != null ? `${parsed.consumption_kwh} kWh` : parsed.consumption_m3 != null ? `${parsed.consumption_m3} m³` : null],
                ["Account", parsed.account_number],
                ["Confidence", parsed.confidence],
              ].map(([label, value]) =>
                value ? (
                  <div key={String(label)}>
                    <div style={{ fontSize: 11, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>{String(label)}</div>
                    <div style={{ fontSize: 14, color: "#e5e7eb", marginTop: 2 }}>{String(value)}</div>
                  </div>
                ) : null
              )}
            </div>
          </div>

          {parsed.translated_summary ? (
            <div style={{ ...cardStyle, marginTop: 16, borderLeft: "3px solid #2563eb" }}>
              <div style={{ fontSize: 11, color: "#2563eb", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6, fontWeight: 600 }}>
                🌍 English Summary
              </div>
              <div style={{ fontSize: 14, color: "#e5e7eb", lineHeight: 1.5 }}>
                {String(parsed.translated_summary)}
              </div>
            </div>
          ) : null}

          {Array.isArray(parsed.line_items) && parsed.line_items.length > 0 ? (
            <div style={{ ...cardStyle, marginTop: 16 }}>
              <h3 style={{ color: "white", margin: "0 0 12px", fontSize: 14 }}>Line Items</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #2d3148" }}>
                    <th style={{ padding: "8px 0", textAlign: "left", color: "#6b7280", fontSize: 11, textTransform: "uppercase", fontWeight: 600 }}>Description</th>
                    <th style={{ padding: "8px 0", textAlign: "left", color: "#6b7280", fontSize: 11, textTransform: "uppercase", fontWeight: 600 }}>English</th>
                    <th style={{ padding: "8px 0", textAlign: "right", color: "#6b7280", fontSize: 11, textTransform: "uppercase", fontWeight: 600 }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(parsed.line_items as Array<Record<string, unknown>>).map((li, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e2132" }}>
                      <td style={{ padding: "8px 8px 8px 0", color: "#9ca3af" }}>{String(li.description_et ?? "—")}</td>
                      <td style={{ padding: "8px 0", color: "#e5e7eb" }}>{String(li.description_en ?? "—")}</td>
                      <td style={{ padding: "8px 0", textAlign: "right", color: "#22c55e", fontVariantNumeric: "tabular-nums" }}>
                        {li.amount_eur != null ? `€${(li.amount_eur as number).toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {parsed.glossary && typeof parsed.glossary === "object" && Object.keys(parsed.glossary as object).length > 0 ? (
            <div style={{ ...cardStyle, marginTop: 16 }}>
              <h3 style={{ color: "white", margin: "0 0 12px", fontSize: 14 }}>📖 Glossary</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
                {Object.entries(parsed.glossary as Record<string, string>).map(([et, en]) => (
                  <div key={et} style={{ background: "#252838", padding: "8px 12px", borderRadius: 6, fontSize: 13 }}>
                    <span style={{ color: "#9ca3af" }}>{et}</span>
                    <span style={{ color: "#6b7280", margin: "0 6px" }}>→</span>
                    <span style={{ color: "#e5e7eb" }}>{en}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}

      <div style={{ ...cardStyle, marginTop: 24 }}>
        <h3 style={{ color: "white", margin: "0 0 4px", fontSize: 14 }}>Supported Invoice Types</h3>
        <p style={{ color: "#6b7280", fontSize: 12, margin: "0 0 12px" }}>
          Local OCR works best with standard-layout PDF invoices.
          AI (OpenRouter) handles any format, language, or layout using free vision models.
        </p>

        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: "#2563eb", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6, fontWeight: 600 }}>
            Utility Bills (best local OCR accuracy)
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {["Electricity", "Gas", "Water", "Heating", "Internet / Telecom", "Waste Collection", "Housing Association"].map(p => (
              <span key={p} style={{ background: "#1e2640", border: "1px solid #2563eb", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "#93c5fd" }}>
                {p}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
            Any invoice (AI / OpenRouter)
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {["Rent", "Subscriptions", "Services", "Repairs", "Insurance", "Any format or language"].map(p => (
              <span key={p} style={{ background: "#252838", border: "1px solid #374151", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "#d1d5db" }}>
                {p}
              </span>
            ))}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
