import { useEffect, useState } from "react";
import UploadTab from "./components/UploadTab";
import BillsTab from "./components/BillsTab";
import AnalyticsTab from "./components/AnalyticsTab";
import HelpTab from "./components/HelpTab";
import CommunityTab from "./components/CommunityTab";
import LoginScreen from "./components/LoginScreen";
import ErrorBoundary from "./components/ErrorBoundary";
import {
  BarChart2, Receipt, Upload, HelpCircle, LogOut, Users as UsersIcon,
} from "lucide-react";
import { api, type User } from "./api";
import { clearToken, getToken } from "./auth";
import { useIsMobile } from "./hooks/useIsMobile";

type Tab = "upload" | "bills" | "analytics" | "community" | "help";
type AuthState = "loading" | "required" | "authed";

export default function App() {
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshKey, setRefreshKey] = useState(0);
  // Lazy initial: skip the loading state entirely if there's no token to verify.
  const [authState, setAuthState] = useState<AuthState>(() =>
    getToken() ? "loading" : "required",
  );
  const [me, setMe] = useState<User | null>(null);
  const isMobile = useIsMobile();

  const refresh = () => setRefreshKey((k) => k + 1);

  // On mount, validate the stored token by hitting /api/auth/me. The axios
  // 401 interceptor handles expired tokens by emitting `auth:logout`.
  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      // No token means we already initialised to "required" above; nothing to do.
      return;
    }
    api
      .getMe()
      .then((res) => {
        if (cancelled) return;
        setMe(res.data);
        setAuthState("authed");
      })
      .catch(() => {
        if (!cancelled) setAuthState("required");
      });
    const onLogout = () => {
      setMe(null);
      setAuthState("required");
    };
    window.addEventListener("auth:logout", onLogout);
    return () => {
      cancelled = true;
      window.removeEventListener("auth:logout", onLogout);
    };
  }, []);

  const onLoginSuccess = () => {
    api
      .getMe()
      .then((res) => {
        setMe(res.data);
        setAuthState("authed");
      })
      .catch(() => setAuthState("required"));
  };

  const logout = () => {
    clearToken();
    setMe(null);
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
    return <LoginScreen onSuccess={onLoginSuccess} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f1117", color: "#e5e7eb", fontFamily: "system-ui, sans-serif" }}>
      <header style={{
        background: "#1a1d27", borderBottom: "1px solid #2d3148",
        padding: isMobile ? "12px 16px" : "16px 24px",
        display: "flex", alignItems: "center", gap: isMobile ? 8 : 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: isMobile ? 8 : 12 }}>
          <div style={{ width: 32, height: 32, background: "#2563eb", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Receipt size={16} color="white" />
          </div>
          {!isMobile && (
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "white" }}>EE Utility Tracker</div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>Estonia Monthly Bill Analytics</div>
            </div>
          )}
        </div>
        <nav style={{ marginLeft: "auto", display: "flex", gap: isMobile ? 2 : 4, alignItems: "center" }}>
          {([
            ["upload", "Upload", Upload],
            ["bills", "Bills", Receipt],
            ["analytics", "Analytics", BarChart2],
            ["community", "Community", UsersIcon],
            ["help", "Help", HelpCircle],
          ] as [Tab, string, React.ElementType][]).map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              title={label}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: isMobile ? "8px 10px" : "8px 14px",
                borderRadius: 8, border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: 500,
                background: tab === id ? "#2563eb" : "transparent",
                color: tab === id ? "white" : "#9ca3af",
                transition: "all 0.15s",
              }}
            >
              <Icon size={16} />
              {!isMobile && label}
            </button>
          ))}
          {me && (
            <div
              title={me.email ?? me.name ?? ""}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                marginLeft: isMobile ? 4 : 12,
                padding: isMobile ? "4px 6px" : "4px 10px 4px 4px",
                borderRadius: 999,
                border: "1px solid #2d3148",
                background: "#0f1117",
              }}
            >
              {me.picture ? (
                <img
                  src={me.picture}
                  alt=""
                  width={26}
                  height={26}
                  referrerPolicy="no-referrer"
                  style={{ borderRadius: "50%", display: "block" }}
                />
              ) : (
                <div
                  style={{
                    width: 26, height: 26, borderRadius: "50%",
                    background: "#2563eb", color: "white",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 600,
                  }}
                >
                  {(me.name ?? me.email ?? "?").slice(0, 1).toUpperCase()}
                </div>
              )}
              {!isMobile && (
                <span style={{ fontSize: 12, color: "#d1d5db", maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {me.name ?? me.email}
                </span>
              )}
            </div>
          )}
          <button
            onClick={logout}
            title="Sign out"
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: isMobile ? "8px 10px" : "8px 12px",
              borderRadius: 8, border: "1px solid #2d3148", cursor: "pointer",
              fontSize: 13, background: "transparent", color: "#9ca3af",
              marginLeft: isMobile ? 4 : 8,
            }}
          >
            <LogOut size={14} />
            {!isMobile && "Sign out"}
          </button>
        </nav>
      </header>

      <main style={{ padding: isMobile ? "16px 12px" : "24px", maxWidth: 1280, margin: "0 auto" }}>
        <ErrorBoundary>
          {tab === "upload" && <UploadTab onSuccess={() => { refresh(); setTab("bills"); }} />}
          {tab === "bills" && <BillsTab key={refreshKey} />}
          {tab === "analytics" && <AnalyticsTab key={refreshKey} />}
          {tab === "community" && <CommunityTab key={refreshKey} />}
          {tab === "help" && <HelpTab />}
        </ErrorBoundary>
      </main>
    </div>
  );
}
