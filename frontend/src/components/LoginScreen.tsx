import { useState } from "react";
import { Lock } from "lucide-react";
import axios from "axios";
import { api } from "../api";
import { setToken } from "../auth";

interface Props {
  onSuccess: () => void;
}

export default function LoginScreen({ onSuccess }: Props) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(password);
      setToken(res.data.token);
      onSuccess();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setError("Wrong password.");
      } else {
        setError("Could not reach the server. Check your connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0f1117",
        color: "#e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, sans-serif",
        padding: 24,
      }}
    >
      <form
        onSubmit={submit}
        style={{
          background: "#1a1d27",
          border: "1px solid #2d3148",
          borderRadius: 12,
          padding: 32,
          width: "100%",
          maxWidth: 400,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              background: "#2563eb",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Lock size={20} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "white" }}>Sign in</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>EE Utility Tracker</div>
          </div>
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 13, color: "#9ca3af" }}>Password</span>
          <input
            type="password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              border: "1px solid #2d3148",
              background: "#0f1117",
              color: "#e5e7eb",
              fontSize: 14,
            }}
          />
        </label>

        {error && (
          <div
            style={{
              padding: "8px 12px",
              borderRadius: 6,
              background: "#3a1111",
              border: "1px solid #7f1d1d",
              color: "#fca5a5",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          style={{
            padding: "10px 16px",
            borderRadius: 8,
            border: "none",
            cursor: loading || !password ? "not-allowed" : "pointer",
            background: loading || !password ? "#1e3a8a" : "#2563eb",
            color: "white",
            fontWeight: 600,
            fontSize: 14,
          }}
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
