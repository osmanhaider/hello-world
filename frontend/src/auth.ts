const KEY = "ee-utility-trackly:token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(KEY, token);
  } catch {
    // localStorage disabled (private mode) — token won't persist but the
    // session is still valid for the current page load.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // no-op
  }
}
