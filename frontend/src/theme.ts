/**
 * Theme management.
 *
 * The user picks one of `light`, `dark`, or `system` (default). We persist
 * the choice in `localStorage` and apply `data-theme="light|dark"` on the
 * `<html>` element so CSS vars in `styles/theme.css` switch in unison.
 *
 * `system` resolves to whatever `prefers-color-scheme` says now and follows
 * OS-level changes live (via matchMedia).
 */
import { useCallback, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "ee-utility-trackly:theme";

function readStored(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    // localStorage disabled (private mode) — fall through.
  }
  return "system";
}

function systemPrefers(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyToDocument(resolved: ResolvedTheme): void {
  const root = document.documentElement;
  root.setAttribute("data-theme", resolved);
  root.style.colorScheme = resolved;
}

/**
 * Hook: returns the current mode, the resolved theme, and a setter.
 * Calling this anywhere in the tree is fine — only the topmost call drives
 * the document attribute, but every caller stays in sync via React state.
 */
export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(() => readStored());
  const [systemDark, setSystemDark] = useState<boolean>(() => systemPrefers() === "dark");

  // Derived synchronously from inputs — no setState-in-effect needed.
  const resolved: ResolvedTheme =
    mode === "system" ? (systemDark ? "dark" : "light") : mode;

  // Sync the resolved theme onto the <html> element. DOM is the external
  // system here, so an effect is the right place.
  useEffect(() => {
    applyToDocument(resolved);
  }, [resolved]);

  // Track the OS preference. We always listen so the value is fresh if the
  // user later flips back to "system" mode.
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore — session-only fallback is fine.
    }
  }, []);

  return { mode, resolved, setMode };
}
