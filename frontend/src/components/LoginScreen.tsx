import { useEffect, useRef, useState } from "react";
import { Receipt, AlertCircle, Loader2 } from "lucide-react";
import axios from "axios";
import { api } from "../api";
import { setToken } from "../auth";
import { getGoogleClientId, loadGoogleIdentityServices } from "../google";
import { useTheme } from "../theme";

interface Props {
  onSuccess: () => void;
}

export default function LoginScreen({ onSuccess }: Props) {
  const buttonRef = useRef<HTMLDivElement | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [exchanging, setExchanging] = useState(false);
  const [ready, setReady] = useState(false);
  const clientId = getGoogleClientId();
  const { resolved } = useTheme();
  // Derived from a stable env value, so it doesn't belong in a state update.
  const configError = !clientId
    ? "Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID on the frontend and GOOGLE_CLIENT_ID on the backend."
    : null;
  const error = configError ?? runtimeError;

  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;
    loadGoogleIdentityServices()
      .then(() => {
        if (cancelled || !window.google || !buttonRef.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (resp) => {
            setRuntimeError(null);
            setExchanging(true);
            try {
              const r = await api.loginWithGoogle(resp.credential);
              setToken(r.data.token);
              onSuccess();
            } catch (e) {
              if (axios.isAxiosError(e)) {
                const detail = (e.response?.data as { detail?: string } | undefined)?.detail;
                setRuntimeError(detail ?? "Sign-in failed. Please try again.");
              } else {
                setRuntimeError("Could not reach the server. Check your connection.");
              }
            } finally {
              setExchanging(false);
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        // The Google button itself doesn't honor our theme tokens, so we ask
        // for the closest match and let it sit on a neutral surface.
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: resolved === "dark" ? "filled_black" : "outline",
          size: "large",
          text: "signin_with",
          shape: "pill",
          width: 300,
        });
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setRuntimeError("Couldn't load Google Sign-In. Try refreshing the page.");
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, onSuccess, resolved]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(1200px 600px at 80% -10%, var(--accent-soft), transparent 60%)," +
          "radial-gradient(800px 500px at -10% 110%, var(--info-soft), transparent 60%)," +
          "var(--bg)",
        color: "var(--text-1)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        className="slide-up"
        style={{
          background: "var(--surface-1)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: 36,
          width: "100%",
          maxWidth: 440,
          display: "flex",
          flexDirection: "column",
          gap: 22,
          alignItems: "center",
          boxShadow: "var(--shadow-lg)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            className="pulse-accent"
            style={{
              width: 48,
              height: 48,
              background: "linear-gradient(135deg, var(--accent), var(--accent-strong))",
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "var(--shadow-accent)",
            }}
          >
            <Receipt size={22} color="var(--text-on-accent)" />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-1)", letterSpacing: -0.2 }}>
              EE Utility Tracker
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>
              Sign in to upload and explore bills
            </div>
          </div>
        </div>

        <p style={{ color: "var(--text-2)", fontSize: 13, textAlign: "center", margin: 0, lineHeight: 1.55 }}>
          Use your Google account. Bills are visible to other signed-in users by
          default; mark any bill private with the lock toggle to keep it to yourself.
        </p>

        <div
          ref={buttonRef}
          style={{ minHeight: 48, display: "flex", justifyContent: "center" }}
        />

        {!ready && !error && (
          <div style={{ color: "var(--text-2)", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
            Loading sign-in…
          </div>
        )}

        {exchanging && (
          <div style={{ color: "var(--accent)", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
            Signing you in…
          </div>
        )}

        {error && (
          <div
            className="fade-in"
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              background: "var(--danger-soft)",
              border: "1px solid var(--danger)",
              color: "var(--danger)",
              fontSize: 13,
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
              width: "100%",
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
