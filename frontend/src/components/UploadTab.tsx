import { useState, useCallback } from "react";
import { api } from "../api";
import { Upload, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

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

type Status = "idle" | "uploading" | "success" | "error";

export default function UploadTab({ onSuccess }: UploadTabProps) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleFile = useCallback(async (file: File) => {
    setStatus("uploading");
    setParsed(null);
    setErrorMsg("");
    try {
      const res = await api.uploadBill(file);
      setParsed(res.data.parsed);
      setStatus("success");
      setTimeout(onSuccess, 2000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setErrorMsg(msg);
      setStatus("error");
    }
  }, [onSuccess]);

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

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ color: "white", marginBottom: 8, fontSize: 22 }}>Upload Utility Bill</h2>
      <p style={{ color: "#9ca3af", marginBottom: 24, fontSize: 14 }}>
        Upload a photo or PDF of your Estonian utility bill. Claude AI will extract all details automatically.
      </p>

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
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept="image/*,.pdf"
          style={{ display: "none" }}
          onChange={onFileChange}
        />
        {status === "uploading" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <Loader2 size={40} color="#2563eb" style={{ animation: "spin 1s linear infinite" }} />
            <p style={{ color: "#9ca3af", margin: 0 }}>Analyzing receipt with Claude AI…</p>
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

      {status === "success" && parsed && (
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
              ["Period", parsed.period_start && parsed.period_end ? `${parsed.period_start} → ${parsed.period_end}` : null],
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
      )}

      <div style={{ ...cardStyle, marginTop: 24 }}>
        <h3 style={{ color: "white", margin: "0 0 12px", fontSize: 14 }}>Supported Estonian Providers</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {["Eesti Energia", "Elering", "Tallinna Vesi", "Gasum", "Telia", "Elisa", "Tele2", "Adven", "Fortum", "Utilitas"].map(p => (
            <span key={p} style={{ background: "#252838", border: "1px solid #374151", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "#d1d5db" }}>
              {p}
            </span>
          ))}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
