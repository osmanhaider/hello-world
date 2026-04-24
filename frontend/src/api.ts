import axios from "axios";

const BASE = "http://localhost:8000";

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
  by_type: TypeStat[];
  by_month: MonthTypeStat[];
  by_year: YearStat[];
  seasonal: SeasonalStat[];
  by_provider: ProviderStat[];
  monthly_total: MonthlyTotal[];
  line_item_trends: LineItemTrend[];
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
  uploadBill: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return axios.post<{ id: string; parsed: Record<string, unknown> }>(`${BASE}/api/bills/upload`, fd);
  },
  listBills: () => axios.get<Bill[]>(`${BASE}/api/bills`),
  deleteBill: (id: string) => axios.delete(`${BASE}/api/bills/${id}`),
  updateBill: (id: string, data: Partial<Bill>) => axios.put(`${BASE}/api/bills/${id}`, data),
  getAnalytics: () => axios.get<AnalyticsSummary>(`${BASE}/api/analytics/summary`),
};
