import { useEffect, useState } from "react";
import { api, type AnalyticsSummary } from "../api";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, Loader2, AlertCircle } from "lucide-react";

const COLORS: Record<string, string> = {
  electricity: "#f59e0b",
  gas: "#f97316",
  water: "#3b82f6",
  heating: "#ef4444",
  internet: "#8b5cf6",
  waste: "#6b7280",
  other: "#9ca3af",
};

const MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const PALETTE = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#f97316", "#06b6d4"];

function colorFor(t: string, i = 0) {
  return COLORS[t] ?? PALETTE[i % PALETTE.length];
}

function fmtEur(v: unknown): [string, string] {
  return [`€${(v as number).toFixed(2)}`, ""];
}


function PctBadge({ v, label }: { v: number | null; label: string }) {
  if (v == null) return <span style={{ color: "#4b5563", fontSize: 12 }}>—</span>;
  const pos = v > 0;
  const flat = Math.abs(v) < 0.5;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      color: flat ? "#9ca3af" : pos ? "#ef4444" : "#22c55e",
      fontSize: 13, fontWeight: 600, fontVariantNumeric: "tabular-nums",
    }}>
      {flat ? <Minus size={12} /> : pos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {pos ? "+" : ""}{v.toFixed(1)}%
      <span style={{ color: "#6b7280", fontWeight: 400, fontSize: 11 }}>{label}</span>
    </span>
  );
}

function StatCard({ label, value, sub, trend }: { label: string; value: string; sub?: string; trend?: "up" | "down" | "flat" }) {
  return (
    <div style={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 12, padding: "20px 24px" }}>
      <div style={{ fontSize: 12, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "white" }}>{value}</div>
      {sub && (
        <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
          {trend === "up" && <TrendingUp size={12} color="#ef4444" />}
          {trend === "down" && <TrendingDown size={12} color="#22c55e" />}
          {trend === "flat" && <Minus size={12} color="#9ca3af" />}
          {sub}
        </div>
      )}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 style={{ color: "white", fontSize: 16, fontWeight: 600, margin: "32px 0 16px" }}>{children}</h3>;
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 12, padding: 24 }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "white" }}>{title}</div>
        {subtitle && <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}

const tooltipStyle = {
  contentStyle: { background: "#1a1d27", border: "1px solid #374151", borderRadius: 8, fontSize: 13 },
  labelStyle: { color: "#9ca3af" },
};

export default function AnalyticsTab() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics().then(r => { setData(r.data); setLoading(false); });
  }, []);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200, gap: 12, color: "#9ca3af" }}>
      <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} /> Loading analytics…
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (!data || data.monthly_total.length === 0) return (
    <div style={{ textAlign: "center", padding: 80, color: "#6b7280" }}>
      <AlertCircle size={40} style={{ marginBottom: 12 }} />
      <p>No data yet. Upload some bills to see analytics!</p>
    </div>
  );

  const totalSpend = data.by_type.reduce((s, t) => s + t.total_eur, 0);
  const latestMonth = data.monthly_total[data.monthly_total.length - 1];
  const prevMonth = data.monthly_total[data.monthly_total.length - 2];
  const momChange = latestMonth.mom_delta_pct ?? (prevMonth ? ((latestMonth.total_eur - prevMonth.total_eur) / prevMonth.total_eur * 100) : null);
  const latestYoy = latestMonth.yoy_delta_pct;

  const momRows = data.monthly_total
    .filter(r => r.mom_delta_pct != null)
    .map(r => ({ month: r.month, delta: r.mom_delta_pct!, eur: r.mom_delta_eur!, total: r.total_eur }));

  const types = Array.from(new Set(data.by_month.map(r => r.utility_type)));

  const monthlyStacked: Record<string, Record<string, number | string>> = {};
  for (const r of data.by_month) {
    if (!monthlyStacked[r.month]) monthlyStacked[r.month] = { month: r.month };
    monthlyStacked[r.month][r.utility_type] = r.total_eur;
  }
  const stackedRows = Object.values(monthlyStacked).sort((a, b) => String(a.month).localeCompare(String(b.month)));

  const seasonalMap: Record<string, Record<string, number | string>> = {};
  for (const r of data.seasonal) {
    const mn = MONTH_NAMES[parseInt(r.month_num)];
    if (!seasonalMap[mn]) seasonalMap[mn] = { month: mn };
    seasonalMap[mn][r.utility_type] = parseFloat(r.avg_eur.toFixed(2));
  }
  const seasonalRows = Object.values(seasonalMap).sort((a, b) =>
    MONTH_NAMES.indexOf(String(a.month)) - MONTH_NAMES.indexOf(String(b.month))
  );

  const yoyRows = data.monthly_total
    .filter(r => r.yoy_delta_pct != null)
    .map(r => ({ month: r.month, delta: r.yoy_delta_pct!, eur: r.yoy_delta_eur! }));

  const radarTypes = types.slice(0, 5);
  const radarData = ["Winter", "Spring", "Summer", "Autumn"].map((season, si) => {
    const entry: Record<string, string | number> = { season };
    const months = [[12, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]][si];
    for (const t of radarTypes) {
      const relevant = data.seasonal.filter(r => months.includes(parseInt(r.month_num)) && r.utility_type === t);
      entry[t] = relevant.length ? parseFloat((relevant.reduce((s, r) => s + r.avg_eur, 0) / relevant.length).toFixed(2)) : 0;
    }
    return entry;
  });

  const topProviders = data.by_provider.slice(0, 8);

  const annualByType: Record<string, Record<string, number | string>> = {};
  for (const r of data.by_year) {
    if (!annualByType[r.year]) annualByType[r.year] = { year: r.year };
    annualByType[r.year][r.utility_type] = parseFloat(r.total_eur.toFixed(2));
  }
  const annualRows = Object.values(annualByType).sort((a, b) => String(a.year).localeCompare(String(b.year)));

  const grid2 = { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 20 };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 8 }}>
        <div>
          <h2 style={{ color: "white", margin: 0, fontSize: 22 }}>Analytics Dashboard</h2>
          <p style={{ color: "#9ca3af", margin: "4px 0 0", fontSize: 13 }}>
            {data.by_type.reduce((s, t) => s + t.bill_count, 0)} bills · {types.length} utility types
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16, marginBottom: 8 }}>
        <StatCard label="Total Spend" value={`€${totalSpend.toFixed(2)}`} />
        <StatCard
          label="Latest Month"
          value={`€${latestMonth.total_eur.toFixed(2)}`}
          sub={momChange != null ? `${momChange > 0 ? "+" : ""}${momChange.toFixed(1)}% MoM` : undefined}
          trend={momChange == null ? undefined : momChange > 5 ? "up" : momChange < -5 ? "down" : "flat"}
        />
        {latestYoy != null && (
          <StatCard
            label="YoY Change"
            value={`${latestYoy > 0 ? "+" : ""}${latestYoy.toFixed(1)}%`}
            sub={latestMonth.yoy_delta_eur != null ? `€${latestMonth.yoy_delta_eur > 0 ? "+" : ""}${latestMonth.yoy_delta_eur.toFixed(2)} vs same month last year` : "vs same month last year"}
            trend={latestYoy > 5 ? "up" : latestYoy < -5 ? "down" : "flat"}
          />
        )}
        <StatCard label="3-Month Avg" value={`€${latestMonth.rolling_avg_3m.toFixed(2)}`} sub="rolling average" />
        <StatCard label="Highest Single Bill" value={`€${Math.max(...data.by_type.map(t => t.max_eur)).toFixed(2)}`} />
        <StatCard label="Monthly Avg (all time)" value={`€${(totalSpend / Math.max(data.monthly_total.length, 1)).toFixed(2)}`} />
        {data.by_type.find(t => t.total_kwh) && (
          <StatCard label="Total Electricity" value={`${data.by_type.find(t => t.total_kwh)!.total_kwh!.toFixed(0)} kWh`} />
        )}
      </div>

      {/* 1. Total spend over time */}
      <SectionTitle>📈 1. Monthly Spending Trend &amp; Rolling Average</SectionTitle>
      <ChartCard title="Total Monthly Spend" subtitle="Blue area = actual spend · Dashed = 3-month rolling average">
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data.monthly_total}>
            <defs>
              <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
            <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 12 }} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
            <Tooltip {...tooltipStyle} formatter={fmtEur} />
            <Legend />
            <Area type="monotone" dataKey="total_eur" stroke="#2563eb" fill="url(#totalGrad)" name="Monthly Total" strokeWidth={2} />
            <Line type="monotone" dataKey="rolling_avg_3m" stroke="#f59e0b" strokeDasharray="5 5" name="3-Month Avg" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 2. MoM & YoY % Change */}
      {(momRows.length > 0 || yoyRows.length > 0) && (
        <>
          <SectionTitle>📉 2. Month-over-Month &amp; Year-over-Year % Change</SectionTitle>
          <div style={grid2}>
            {momRows.length > 0 && (
              <ChartCard title="Month-over-Month Change" subtitle="Green = cheaper than previous month · Red = more expensive">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={momRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                    <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `${v}%`} />
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(v, name) => name === "delta"
                        ? [`${(v as number) > 0 ? "+" : ""}${(v as number).toFixed(1)}%`, "MoM %"]
                        : [`€${(v as number) > 0 ? "+" : ""}${(v as number).toFixed(2)}`, "MoM €"]}
                    />
                    <Bar dataKey="delta" name="MoM %" radius={[3, 3, 0, 0]}>
                      {momRows.map((r, i) => (
                        <Cell key={i} fill={r.delta > 0 ? "#ef4444" : "#22c55e"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}

            {yoyRows.length > 0 && (
              <ChartCard title="Year-over-Year Change" subtitle="Green = cheaper than same month last year · Red = more expensive">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={yoyRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                    <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `${v}%`} />
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(v, name) => name === "delta"
                        ? [`${(v as number) > 0 ? "+" : ""}${(v as number).toFixed(1)}%`, "YoY %"]
                        : [`€${(v as number) > 0 ? "+" : ""}${(v as number).toFixed(2)}`, "YoY €"]}
                    />
                    <Bar dataKey="delta" name="YoY %" radius={[3, 3, 0, 0]}>
                      {yoyRows.map((r, i) => (
                        <Cell key={i} fill={r.delta > 0 ? "#ef4444" : "#22c55e"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            )}
          </div>

          {/* Change table */}
          <div style={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 12, overflow: "hidden", marginTop: 20 }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid #2d3148", fontSize: 14, fontWeight: 600, color: "#e5e7eb" }}>
              Change Metrics — All Months
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #2d3148" }}>
                    {["Month", "Total (€)", "MoM Change", "MoM (€)", "YoY Change", "YoY (€)"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", color: "#6b7280", fontWeight: 600, fontSize: 11, textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...data.monthly_total].reverse().map((row, i) => (
                    <tr key={row.month} style={{ borderBottom: i < data.monthly_total.length - 1 ? "1px solid #1e2132" : "none" }}>
                      <td style={{ padding: "10px 16px", color: "#e5e7eb", fontWeight: 500 }}>{row.month}</td>
                      <td style={{ padding: "10px 16px", color: "#22c55e", fontVariantNumeric: "tabular-nums" }}>€{row.total_eur.toFixed(2)}</td>
                      <td style={{ padding: "10px 16px" }}><PctBadge v={row.mom_delta_pct} label="MoM" /></td>
                      <td style={{ padding: "10px 16px", color: row.mom_delta_eur == null ? "#4b5563" : row.mom_delta_eur > 0 ? "#ef4444" : "#22c55e", fontVariantNumeric: "tabular-nums", fontSize: 13 }}>
                        {row.mom_delta_eur != null ? `${row.mom_delta_eur > 0 ? "+" : ""}€${row.mom_delta_eur.toFixed(2)}` : "—"}
                      </td>
                      <td style={{ padding: "10px 16px" }}><PctBadge v={row.yoy_delta_pct} label="YoY" /></td>
                      <td style={{ padding: "10px 16px", color: row.yoy_delta_eur == null ? "#4b5563" : row.yoy_delta_eur > 0 ? "#ef4444" : "#22c55e", fontVariantNumeric: "tabular-nums", fontSize: 13 }}>
                        {row.yoy_delta_eur != null ? `${row.yoy_delta_eur > 0 ? "+" : ""}€${row.yoy_delta_eur.toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* 3. Breakdown by type */}
      <SectionTitle>🗂️ 3. Spend Breakdown by Utility Type</SectionTitle>
      <div style={grid2}>
        <ChartCard title="Monthly Stacked by Type" subtitle="See which utilities drive costs each month">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stackedRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
              <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 11 }} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
              <Tooltip {...tooltipStyle} formatter={fmtEur} />
              <Legend />
              {types.map((t, i) => (
                <Bar key={t} dataKey={t} stackId="a" fill={colorFor(t, i)} name={t} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Share of Total Spend" subtitle="Cumulative share per category">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data.by_type}
                dataKey="total_eur"
                nameKey="utility_type"
                cx="50%" cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.by_type.map((entry, i) => (
                  <Cell key={entry.utility_type} fill={colorFor(entry.utility_type, i)} />
                ))}
              </Pie>
              <Tooltip {...tooltipStyle} formatter={fmtEur} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* 4. Seasonal patterns */}
      <SectionTitle>🌡️ 4. Seasonal Cost Patterns</SectionTitle>
      <div style={grid2}>
        <ChartCard title="Average Bill by Calendar Month" subtitle="Reveals heating spikes in winter, A/C in summer">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={seasonalRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
              <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 12 }} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
              <Tooltip {...tooltipStyle} formatter={fmtEur} />
              <Legend />
              {types.map((t, i) => (
                <Bar key={t} dataKey={t} fill={colorFor(t, i)} name={t} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Seasonal Radar Profile" subtitle="Shape = energy use pattern across 4 seasons">
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={90}>
              <PolarGrid stroke="#2d3148" />
              <PolarAngleAxis dataKey="season" tick={{ fill: "#9ca3af", fontSize: 13 }} />
              {radarTypes.map((t, i) => (
                <Radar key={t} name={t} dataKey={t} stroke={colorFor(t, i)} fill={colorFor(t, i)} fillOpacity={0.15} />
              ))}
              <Legend />
              <Tooltip {...tooltipStyle} formatter={fmtEur} />
            </RadarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* 5. Year-over-year annual view */}
      {annualRows.length > 1 && (
        <>
          <SectionTitle>📅 5. Annual Spend Comparison</SectionTitle>
          <ChartCard title="Annual Spend by Category" subtitle="Compare total utility cost across years">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={annualRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                <XAxis dataKey="year" tick={{ fill: "#6b7280", fontSize: 12 }} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
                <Tooltip {...tooltipStyle} formatter={fmtEur} />
                <Legend />
                {types.map((t, i) => (
                  <Bar key={t} dataKey={t} fill={colorFor(t, i)} name={t} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </>
      )}

      {/* 6. Provider breakdown */}
      {topProviders.length > 0 && (
        <>
          <SectionTitle>🏢 6. Spend by Provider</SectionTitle>
          <ChartCard title="Top Providers by Total Spend" subtitle="Identify your most expensive suppliers">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topProviders} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
                <YAxis type="category" dataKey="provider" tick={{ fill: "#9ca3af", fontSize: 12 }} width={120} />
                <Tooltip {...tooltipStyle} formatter={fmtEur} />
                <Bar dataKey="total_eur" fill="#2563eb" name="Total Spend" radius={[0, 4, 4, 0]}>
                  {topProviders.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </>
      )}

      {/* 7. Per-type trend lines */}
      <SectionTitle>📊 7. Per-Utility Trend Lines</SectionTitle>
      <ChartCard title="Each Utility Type Over Time" subtitle="A sudden spike = price change or leak">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={stackedRows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
            <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 11 }} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} tickFormatter={v => `€${v}`} />
            <Tooltip {...tooltipStyle} formatter={fmtEur} />
            <Legend />
            {types.map((t, i) => (
              <Line key={t} type="monotone" dataKey={t} stroke={colorFor(t, i)} name={t} strokeWidth={2} dot={{ r: 3 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 8. Summary stats table */}
      <SectionTitle>🔢 8. Summary Statistics by Type</SectionTitle>
      <div style={{ background: "#1a1d27", border: "1px solid #2d3148", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #2d3148" }}>
              {["Type", "Bills", "Total", "Avg/Month", "Min", "Max", "Consumption"].map(h => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", color: "#6b7280", fontWeight: 600, fontSize: 12, textTransform: "uppercase" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.by_type.map((row, i) => (
              <tr key={row.utility_type} style={{ borderBottom: i < data.by_type.length - 1 ? "1px solid #1e2132" : "none" }}>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: colorFor(row.utility_type, i), display: "inline-block" }} />
                    <span style={{ color: "white", textTransform: "capitalize" }}>{row.utility_type}</span>
                  </span>
                </td>
                <td style={{ padding: "12px 16px", color: "#9ca3af" }}>{row.bill_count}</td>
                <td style={{ padding: "12px 16px", color: "#22c55e", fontWeight: 600 }}>€{row.total_eur.toFixed(2)}</td>
                <td style={{ padding: "12px 16px", color: "#e5e7eb" }}>€{row.avg_eur.toFixed(2)}</td>
                <td style={{ padding: "12px 16px", color: "#9ca3af" }}>€{row.min_eur.toFixed(2)}</td>
                <td style={{ padding: "12px 16px", color: "#9ca3af" }}>€{row.max_eur.toFixed(2)}</td>
                <td style={{ padding: "12px 16px", color: "#9ca3af" }}>
                  {row.total_kwh ? `${row.total_kwh.toFixed(0)} kWh` : row.total_m3 ? `${row.total_m3.toFixed(1)} m³` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ height: 40 }} />
    </div>
  );
}
