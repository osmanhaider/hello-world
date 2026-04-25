import { useCallback, useEffect, useMemo, useState } from "react";
import { Users as UsersIcon, Globe, Loader2, AlertCircle } from "lucide-react";
import { api, type Bill, type CommunityUser } from "../api";
import AnalyticsTab from "./AnalyticsTab";
import { useIsMobile } from "../hooks/useIsMobile";

const UTILITY_ICONS: Record<string, string> = {
  electricity: "⚡", gas: "🔥", water: "💧",
  heating: "♨️", internet: "🌐", waste: "🗑️", other: "📄",
};

const TYPE_COLORS: Record<string, string> = {
  electricity: "#f59e0b", gas: "#f97316", water: "#0ea5e9",
  heating: "#dc2626", internet: "#8b5cf6", waste: "#64748b", other: "#94a3b8",
};

export default function CommunityTab() {
  const [users, setUsers] = useState<CommunityUser[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingBills, setLoadingBills] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    let cancelled = false;
    api.listCommunityUsers()
      .then((r) => { if (!cancelled) setUsers(r.data); })
      .catch(() => { if (!cancelled) setError("Couldn't load community users."); })
      .finally(() => { if (!cancelled) setLoadingUsers(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Showing the loader on user-picker changes is the whole point of this
    // effect — disabling the rule here is intentional, not an oversight.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingBills(true);
    api.listCommunityBills(selectedUserId ?? undefined)
      .then((r) => { if (!cancelled) setBills(r.data); })
      .catch(() => { if (!cancelled) setError("Couldn't load community bills."); })
      .finally(() => { if (!cancelled) setLoadingBills(false); });
    return () => { cancelled = true; };
  }, [selectedUserId]);

  const analyticsSource = useCallback(
    () => api.getCommunityAnalytics(selectedUserId ?? undefined),
    [selectedUserId],
  );

  const totalEur = useMemo(
    () => bills.reduce((s, b) => s + (b.amount_eur ?? 0), 0),
    [bills],
  );

  const cardStyle = {
    background: "#1a1d27",
    borderRadius: 12,
    border: "1px solid #2d3148",
  };

  const selectedUser = users.find((u) => u.id === selectedUserId) ?? null;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ color: "white", margin: 0, fontSize: 22 }}>Community</h2>
        <p style={{ color: "#9ca3af", margin: "4px 0 0", fontSize: 13 }}>
          Insights from every signed-in user. Pick a person or browse all of them at once.
          Anything anyone marks private stays out of view here.
        </p>
      </div>

      <div style={{ ...cardStyle, padding: 12, marginBottom: 16, overflowX: "auto" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: isMobile ? "nowrap" : "wrap" }}>
          <UserChip
            active={selectedUserId === null}
            onClick={() => setSelectedUserId(null)}
            icon={<Globe size={14} />}
            primary="All users"
            secondary={`${users.reduce((n, u) => n + u.bill_count, 0)} bills`}
          />
          {users.map((u) => (
            <UserChip
              key={u.id}
              active={selectedUserId === u.id}
              onClick={() => setSelectedUserId(u.id)}
              picture={u.picture_url ?? null}
              primary={u.name ?? u.email ?? "Anon"}
              secondary={`${u.bill_count} bill${u.bill_count === 1 ? "" : "s"}`}
            />
          ))}
          {loadingUsers && (
            <span style={{ display: "flex", alignItems: "center", gap: 6, color: "#9ca3af", fontSize: 12, padding: "0 8px" }}>
              <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
              Loading users…
            </span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ ...cardStyle, padding: 12, marginBottom: 16, borderLeft: "3px solid #ef4444", display: "flex", gap: 8, alignItems: "center", color: "#fca5a5", fontSize: 13 }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <AnalyticsTab source={analyticsSource} reloadKey={selectedUserId ? 1 : 0} />

      <div style={{ marginTop: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ color: "white", margin: 0, fontSize: 16 }}>
            {selectedUser
              ? <>Public bills from <strong>{selectedUser.name ?? selectedUser.email}</strong></>
              : "Recent public bills"}
          </h3>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            {bills.length} bill{bills.length === 1 ? "" : "s"} · Total: <strong style={{ color: "#22c55e" }}>€{totalEur.toFixed(2)}</strong>
          </div>
        </div>
        {loadingBills ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#9ca3af", padding: 24 }}>
            <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> Loading bills…
          </div>
        ) : bills.length === 0 ? (
          <div style={{ ...cardStyle, padding: 32, textAlign: "center", color: "#6b7280" }}>
            <UsersIcon size={28} style={{ marginBottom: 8 }} />
            <div>No public bills here yet.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {bills.map((bill) => {
              const color = TYPE_COLORS[bill.utility_type ?? "other"] ?? "#9ca3af";
              return (
                <div key={bill.id} style={{ ...cardStyle, padding: isMobile ? "10px 12px" : "14px 18px", display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{ width: 34, height: 34, borderRadius: 8, background: `${color}22`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>
                    {UTILITY_ICONS[bill.utility_type ?? "other"] ?? "📄"}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 600, color: "white", fontSize: 14 }}>{bill.provider ?? "Unknown Provider"}</span>
                      {bill.utility_type && (
                        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 20, background: `${color}22`, color, border: `1px solid ${color}44`, textTransform: "capitalize" }}>
                          {bill.utility_type}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 2, display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      <span>{bill.bill_date ?? bill.upload_date?.slice(0, 10)}</span>
                      <span style={{ color: "#374151" }}>·</span>
                      {bill.owner_picture ? (
                        <img src={bill.owner_picture} alt="" width={14} height={14} referrerPolicy="no-referrer" style={{ borderRadius: "50%" }} />
                      ) : null}
                      <span>{bill.owner_name ?? "Unknown"}</span>
                    </div>
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 16, color: "#22c55e", flexShrink: 0 }}>
                    {bill.amount_eur != null ? `€${bill.amount_eur.toFixed(2)}` : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

interface UserChipProps {
  active: boolean;
  onClick: () => void;
  picture?: string | null;
  icon?: React.ReactNode;
  primary: string;
  secondary: string;
}

function UserChip({ active, onClick, picture, icon, primary, secondary }: UserChipProps) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "6px 12px 6px 6px",
        borderRadius: 999,
        border: `1px solid ${active ? "#2563eb" : "#2d3148"}`,
        background: active ? "#1e2640" : "#0f1117",
        color: active ? "#dbeafe" : "#d1d5db",
        cursor: "pointer",
        fontSize: 12,
        flexShrink: 0,
      }}
    >
      {picture ? (
        <img src={picture} alt="" width={26} height={26} referrerPolicy="no-referrer" style={{ borderRadius: "50%" }} />
      ) : (
        <div style={{ width: 26, height: 26, borderRadius: "50%", background: active ? "#2563eb" : "#1f2937", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>
          {icon ?? primary.slice(0, 1).toUpperCase()}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", lineHeight: 1.1 }}>
        <span style={{ fontWeight: 600 }}>{primary}</span>
        <span style={{ color: "#9ca3af", fontSize: 11 }}>{secondary}</span>
      </div>
    </button>
  );
}
