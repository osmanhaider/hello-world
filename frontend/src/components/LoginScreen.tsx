import { useEffect, useRef, useState } from "react";
import { Receipt, AlertCircle, Loader2 } from "lucide-react";
import axios from "axios";
import { api } from "../api";
import { setToken } from "../auth";
import { getGoogleClientId, loadGoogleIdentityServices } from "../google";

interface Props {
  onSuccess: () => void;
}

export default function LoginScreen({ onSuccess }: Props) {
  const buttonRef = useRef<HTMLDivElement | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [exchanging, setExchanging] = useState(false);
  const [ready, setReady] = useState(false);
  const clientId = getGoogleClientId();
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
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "filled_blue",
          size: "large",
          text: "signin_with",
          shape: "pill",
          width: 280,
        });
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setRuntimeError("Couldn't load Google Sign-In. Try refreshing the page.");
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, onSuccess]);

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
      <div
        style={{
          background: "#1a1d27",
          border: "1px solid #2d3148",
          borderRadius: 12,
          padding: 32,
          width: "100%",
          maxWidth: 420,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              background: "#2563eb",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Receipt size={22} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "white" }}>
              EE Utility Tracker
            </div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>
              Sign in to upload and explore bills
            </div>
          </div>
        </div>

        <p style={{ color: "#9ca3af", fontSize: 13, textAlign: "center", margin: 0 }}>
          Use your Google account. Your bills will be visible to other signed-in users
          unless you mark a bill private.
        </p>

        <div
          ref={buttonRef}
          style={{ minHeight: 44, display: "flex", justifyContent: "center" }}
        />

        {!ready && !error && (
          <div style={{ color: "#9ca3af", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
            Loading sign-in…
          </div>
        )}

        {exchanging && (
          <div style={{ color: "#93c5fd", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
            Signing you in…
          </div>
        )}

        {error && (
          <div
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              background: "#3a1111",
              border: "1px solid #7f1d1d",
              color: "#fca5a5",
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

        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}
