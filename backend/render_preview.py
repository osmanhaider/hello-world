"""Render the Analytics dashboard as ASCII preview — mirrors exactly what
the React frontend would draw using the same /api/analytics/summary JSON."""
import json

d = json.load(open("/tmp/analytics.json"))
W = 82
BAR = "█"


def line(ch="─"):
    return ch * W


def box(title):
    print("┌" + line("─")[1:-1] + "┐")
    print("│ " + title.ljust(W - 4) + " │")
    print("└" + line("─")[1:-1] + "┘")


def hbar(v, maxv, width=30):
    n = int(round(abs(v) / max(abs(maxv), 0.001) * width))
    return BAR * n


# ──────────────────────────────────────────────────────────────────────────
print("\n" + "═" * W)
print("  📊 ANALYTICS DASHBOARD — Tehnika TN 22 Korteriühistu".ljust(W))
print(f"  {d['by_type'][0]['bill_count']} bills · 1 utility category · 3 months of data".ljust(W))
print("═" * W)

# ── KPI cards ─────────────────────────────────────────────────────────────
mt = d["monthly_total"]
latest = mt[-1]
total = d["by_type"][0]["total_eur"]
maxm = max(r["total_eur"] for r in mt)

print("\n🎯 KPI CARDS (top row)")
print("┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐")
print(f"│ TOTAL SPEND      │ LATEST MONTH     │ YoY CHANGE       │ 3-MONTH AVG      │")
print(f"│ €{total:>7.2f}         │ €{latest['total_eur']:>7.2f}         │ (no prior year)  │ €{latest['rolling_avg_3m']:>7.2f}         │")
print(f"│                  │ ↓ {abs(latest['mom_delta_pct']):.1f}% MoM       │                  │ rolling          │")
print("├──────────────────┼──────────────────┼──────────────────┼──────────────────┤")
print(f"│ HIGHEST BILL     │ MONTHLY AVG      │ TOTAL ELEC.      │                  │")
print(f"│ €{maxm:>7.2f}         │ €{total/len(mt):>7.2f}         │ {d['by_type'][0]['total_kwh']:.0f} kWh          │                  │")
print("└──────────────────┴──────────────────┴──────────────────┴──────────────────┘")

# ── Section 1 ─────────────────────────────────────────────────────────────
print("\n📈 1. MONTHLY SPENDING TREND & ROLLING AVERAGE")
print("─" * W)
for r in mt:
    bar = hbar(r["total_eur"], maxm, 40)
    avg_marker = " ← avg"
    print(f"  {r['month']}  {bar:<40}  €{r['total_eur']:>6.2f}   avg3m €{r['rolling_avg_3m']:.2f}")

# ── Section 2: MoM / YoY ─────────────────────────────────────────────────
print("\n📉 2. MONTH-OVER-MONTH & YEAR-OVER-YEAR % CHANGE")
print("─" * W)
print("  Month     Total      MoM %      MoM €        YoY %      YoY €")
print("  " + "─" * (W - 2))
for r in mt:
    mom_p = f"{r['mom_delta_pct']:+.1f}%" if r['mom_delta_pct'] is not None else "   —"
    mom_e = f"€{r['mom_delta_eur']:+.2f}" if r['mom_delta_eur'] is not None else "   —"
    yoy_p = f"{r['yoy_delta_pct']:+.1f}%" if r['yoy_delta_pct'] is not None else "   —"
    yoy_e = f"€{r['yoy_delta_eur']:+.2f}" if r['yoy_delta_eur'] is not None else "   —"
    mom_color = "🟢" if r['mom_delta_pct'] is not None and r['mom_delta_pct'] < 0 else ("🔴" if r['mom_delta_pct'] else "⚪")
    print(f"  {r['month']}   €{r['total_eur']:>6.2f}   {mom_color} {mom_p:>7}  {mom_e:>9}    ⚪ {yoy_p:>7}  {yoy_e:>9}")

# ── Section 9: Unit Price Trends ─────────────────────────────────────────
print("\n💶 9. UNIT PRICE TRENDS (€ per unit, only items with price changes)")
print("─" * W)
lit = d["line_item_trends"]
# Find price-varying items
from collections import defaultdict
prices = defaultdict(dict)
for r in lit:
    if r["unit_price"] is None:
        continue
    prices[r["description_en"]][r["month"]] = (r["unit_price"], r["unit"])

for label, months in prices.items():
    vals = [v[0] for v in months.values()]
    if len(vals) < 2 or max(vals) - min(vals) < 0.001:
        continue
    print(f"  {label[:60]}")
    for m in sorted(months.keys()):
        p, u = months[m]
        print(f"    {m}  €{p:.4f} / {u}")
    trend = ((vals[-1] - vals[0]) / vals[0] * 100) if vals[0] else 0
    arrow = "↓" if trend < -1 else ("↑" if trend > 1 else "→")
    print(f"    {arrow} Trend: {trend:+.1f}% from first to last reading")
    print()

# ── Section 10: Line-item cost comparison ────────────────────────────────
print("🧾 10. LINE-ITEM COST BY MONTH  (all services, stacked)")
print("─" * W)
per_month = defaultdict(lambda: defaultdict(float))
for r in lit:
    per_month[r["month"]][r["description_en"]] += r["amount_eur"]

labels = sorted({r["description_en"] for r in lit})
months_sorted = sorted(per_month.keys())
print(f"  {'Line Item':<45} " + "  ".join(f"{m:>8}" for m in months_sorted))
print("  " + "─" * (W - 2))
for label in labels:
    vals = [per_month[m].get(label, 0.0) for m in months_sorted]
    # Highlight rows that vary significantly
    diff = max(vals) - min(vals)
    marker = " ⚡" if diff > 10 else ("  " if diff > 1 else "  ")
    print(f" {marker}{label[:43]:<44} " + "  ".join(f"€{v:>6.2f}" for v in vals))

# ── Section 11: Price vs Consumption Decomposition ───────────────────────
print("\n⚖️  11. PRICE vs CONSUMPTION DECOMPOSITION")
print("─" * W)
print("  Formula:  price_effect = (new_price − old_price) × old_qty")
print("            vol_effect   = old_price × (new_qty − old_qty)")
print()
print(f"  {'Line Item':<42} {'Month':<10} {'Price €':>10} {'Vol €':>10} {'Total €':>10}  Interpretation")
print("  " + "─" * (W - 2))

by_label = defaultdict(list)
for r in lit:
    if r["unit_price"] is not None and r["quantity"]:
        by_label[r["description_en"]].append(r)
for label, arr in by_label.items():
    arr.sort(key=lambda x: x["month"])
    for i in range(1, len(arr)):
        prev, cur = arr[i-1], arr[i]
        pe = (cur["unit_price"] - prev["unit_price"]) * prev["quantity"]
        ve = prev["unit_price"] * (cur["quantity"] - prev["quantity"])
        tot = cur["amount_eur"] - prev["amount_eur"]
        # interpretation
        if abs(pe) < 0.01 and abs(ve) < 0.01:
            interp = "Unchanged"
        elif pe > 0 and ve > 0:
            interp = "Higher price + more usage"
        elif pe > 0 and ve < 0:
            interp = "Price hike (usage ↓ offset)"
        elif pe < 0 and ve > 0:
            interp = "Cheaper rate + more usage"
        else:
            interp = "Lower price + less usage"
        # only show material rows
        if abs(tot) < 0.5:
            continue
        print(f"  {label[:40]:<42} {cur['month']:<10} {pe:>+10.2f} {ve:>+10.2f} {tot:>+10.2f}  {interp}")

# ── Section 12: Month-vs-Month comparison ────────────────────────────────
print("\n📋 12. LINE-ITEM COMPARISON: 2 most recent months side by side")
print("─" * W)
# Use the last two months
m_prev, m_curr = months_sorted[-2], months_sorted[-1]
print(f"  {'Line Item':<42} {m_prev:>10} {m_curr:>10} {'Δ €':>10} {'Δ €/unit':>12}")
print("  " + "─" * (W - 2))

by_label_recent = defaultdict(dict)
for r in lit:
    by_label_recent[r["description_en"]][r["month"]] = r

for label in sorted(by_label_recent.keys()):
    prev = by_label_recent[label].get(m_prev)
    curr = by_label_recent[label].get(m_curr)
    p_amt = f"€{prev['amount_eur']:.2f}" if prev else "—"
    c_amt = f"€{curr['amount_eur']:.2f}" if curr else "—"
    diff = (curr["amount_eur"] if curr else 0) - (prev["amount_eur"] if prev else 0)
    diff_s = f"€{diff:+.2f}" if prev or curr else "—"
    price_diff = ""
    if prev and curr and prev.get("unit_price") is not None and curr.get("unit_price") is not None:
        pd = curr["unit_price"] - prev["unit_price"]
        price_diff = f"€{pd:+.4f}"
    marker = "🔴" if diff > 1 else ("🟢" if diff < -1 else "  ")
    print(f" {marker} {label[:40]:<42} {p_amt:>10} {c_amt:>10} {diff_s:>10} {price_diff:>12}")

# ── Section 7: Summary stats table ────────────────────────────────────────
print("\n🔢 7. SUMMARY STATISTICS BY TYPE")
print("─" * W)
for row in d["by_type"]:
    print(f"  Type: {row['utility_type']}  |  Bills: {row['bill_count']}  |  Total: €{row['total_eur']:.2f}")
    print(f"  Avg: €{row['avg_eur']:.2f}  Min: €{row['min_eur']:.2f}  Max: €{row['max_eur']:.2f}  kWh: {row['total_kwh']}")

print("\n" + "═" * W)
print("  END OF DASHBOARD PREVIEW")
print("═" * W)
