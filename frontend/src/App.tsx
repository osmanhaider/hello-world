import { useEffect, useState } from "react";
import UploadTab from "./components/UploadTab";
import BillsTab from "./components/BillsTab";
import AnalyticsTab from "./components/AnalyticsTab";
import HelpTab from "./components/HelpTab";
import LoginScreen from "./components/LoginScreen";
import ErrorBoundary from "./components/ErrorBoundary";
import { BarChart2, Receipt, Upload, HelpCircle, LogOut } from "lucide-react";
import { api } from "./api";
import { clearToken, getToken } from "./auth";

type Tab = "upload" | "bills" | "analytics" | "help";
type AuthState = "loading" | "required" | "authed" | "disabled";

export default function App() {
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshKey, setRefreshKey] = useState(0);
  const [authState, setAuthState] = useState<AuthState>("loading");

  const refresh = () => setRefreshKey((k) => k + 1);

  // On mount, ask the backend whether auth is required. If it isn't we
  // skip the login screen entirely (local-dev convenience). If it is
  // and we already have a stored token, trust it — the axios interceptor
  // will bounce us back to login on 401 if the token has expired.
  useEffect(() => {
    let cancelled = false;
    api
      .getAuthStatus()
      .then((res) => {
        if (cancelled) return;
        if (!res.data.auth_required) {
          setAuthState("disabled");
        } else if (getToken()) {
          setAuthState("authed");
        } else {
          setAuthState("required");
        }
      })
      .catch(() => {
        if (!cancelled) setAuthState(getToken() ? "authed" : "required");
      });
    const onLogout = () => setAuthState("required");
    window.addEventListener("auth:logout", onLogout);
    return () => {
      cancelled = true;
      window.removeEventListener("auth:logout", onLogout);
    };
  }, []);

  const logout = () => {
    clearToken();
    setAuthState("required");
  };

  if (authState === "loading") {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#0f1117",
          color: "#9ca3af",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        Loading…
      </div>
    );
  }

  if (authState === "required") {
    return <LoginScreen onSuccess={() => setAuthState("authed")} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f1117", color: "#e5e7eb", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ background: "#1a1d27", borderBottom: "1px solid #2d3148", padding: "16px 24px", display: "flex", alignItems: "center", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: 36, height: 36, background: "#2563eb", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Receipt size={18} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "white" }}>EE Utility Tracker</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>Estonia Monthly Bill Analytics</div>
          </div>
        </div>
        <nav style={{ marginLeft: "auto", display: "flex", gap: 4, alignItems: "center" }}>
          {([
            ["upload", "Upload", Upload],
            ["bills", "Bills", Receipt],
            ["analytics", "Analytics", BarChart2],
            ["help", "Help", HelpCircle],
          ] as [Tab, string, React.ElementType][]).map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 16px",
                borderRadius: 8, border: "none", cursor: "pointer", fontSize: 14, fontWeight: 500,
                background: tab === id ? "#2563eb" : "transparent",
                color: tab === id ? "white" : "#9ca3af",
                transition: "all 0.15s",
              }}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
          {authState === "authed" && (
            <button
              onClick={logout}
              title="Sign out"
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
                borderRadius: 8, border: "1px solid #2d3148", cursor: "pointer", fontSize: 13,
                background: "transparent", color: "#9ca3af", marginLeft: 8,
              }}
            >
              <LogOut size={14} />
              Sign out
            </button>
          )}
        </nav>
      </header>

      <main style={{ padding: "24px", maxWidth: 1280, margin: "0 auto" }}>
        <ErrorBoundary>
          {tab === "upload" && <UploadTab onSuccess={() => { refresh(); setTab("bills"); }} />}
          {tab === "bills" && <BillsTab key={refreshKey} />}
          {tab === "analytics" && <AnalyticsTab key={refreshKey} />}
          {tab === "help" && <HelpTab />}
        </ErrorBoundary>
      </main>
    </div>
  );
}
