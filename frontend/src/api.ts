import axios from "axios";
import { clearToken, getToken } from "./auth";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Attach the bearer token to every outgoing request (when present) and
// log the user out automatically on 401 so a stale token can't pin the
// UI to a broken state.
axios.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

axios.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      clearToken();
      // Nudge the app to re-render; LoginScreen listens for this.
      window.dispatchEvent(new Event("auth:logout"));
    }
    return Promise.reject(err);
  },
);

export interface Bill {
  id: string;
  filename: string;
  upload_date: string;
  bill_date: string | null;
  provider: string | null;
  utility_type: string | null;
  amount_eur: number | null;
  consumption_kwh: number | null;
  consumption_m3: number | null;
  period_start: string | null;
  period_end: string | null;
  account_number: string | null;
  address: string | null;
  raw_json: string | null;
  notes: string | null;
}

export interface AnalyticsSummary {
  totals: BillTotals;
  by_type: TypeStat[];
  by_month: MonthTypeStat[];
  by_year: YearStat[];
  seasonal: SeasonalStat[];
  by_provider: ProviderStat[];
  monthly_total: MonthlyTotal[];
  line_item_trends: LineItemTrend[];
}

export interface BillTotals {
  bill_count: number;
  total_eur: number;
  avg_eur: number;
  min_eur: number;
  max_eur: number;
}

export interface LineItemTrend {
  month: string;
  description_en: string;
  description_et: string;
  amount_eur: number;
  quantity: number | null;
  unit: string;
  unit_price: number | null;
}

export interface TypeStat {
  utility_type: string;
  bill_count: number;
  total_eur: number;
  avg_eur: number;
  min_eur: number;
  max_eur: number;
  total_kwh: number | null;
  total_m3: number | null;
}

export interface MonthTypeStat {
  month: string;
  utility_type: string;
  total_eur: number;
  bill_count: number;
}

export interface YearStat {
  year: string;
  utility_type: string;
  total_eur: number;
  avg_monthly_eur: number;
  bill_count: number;
}

export interface SeasonalStat {
  month_num: string;
  avg_eur: number;
  utility_type: string;
}

export interface ProviderStat {
  provider: string;
  bill_count: number;
  total_eur: number;
  avg_eur: number;
}

export interface MonthlyTotal {
  month: string;
  total_eur: number;
  rolling_avg_3m: number;
  mom_delta_eur: number | null;
  mom_delta_pct: number | null;
  yoy_delta_eur: number | null;
  yoy_delta_pct: number | null;
}

export const api = {
  uploadBill: (file: File, parser?: string, model?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (parser) fd.append("parser", parser);
    if (model) fd.append("model", model);
    return axios.post<{ id: string; parsed: Record<string, unknown>; replaced: boolean }>(`${BASE}/api/bills/upload`, fd);
  },
  listBills: () => axios.get<Bill[]>(`${BASE}/api/bills`),
  deleteBill: (id: string) => axios.delete(`${BASE}/api/bills/${id}`),
  updateBill: (id: string, data: Partial<Bill>) => axios.put(`${BASE}/api/bills/${id}`, data),
  getAnalytics: () => axios.get<AnalyticsSummary>(`${BASE}/api/analytics/summary`),
  getOpenRouterModels: () =>
    axios.get<{ models: { id: string; label: string }[]; cached?: boolean; error?: string }>(
      `${BASE}/api/openrouter-models`
    ),
  getAuthStatus: () => axios.get<{ auth_required: boolean }>(`${BASE}/api/auth/status`),
  login: (password: string) =>
    axios.post<{ token: string; auth_required: boolean }>(`${BASE}/api/auth/login`, { password }),
};
