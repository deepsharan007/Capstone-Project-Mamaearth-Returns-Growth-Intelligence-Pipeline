"""
analysis/visualize.py  |  Part 2, Task 11  |  Mamaearth Returns Pipeline

Rebuilds the cleaned data from the raw CSVs (by reusing clean_and_eda.run)
and saves two charts to visualizations/. No numbers are typed by hand.
Run from the repo root:   python analysis/visualize.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # save files without needing a screen
import matplotlib.pyplot as plt
import pandas as pd

from clean_and_eda import run

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "visualizations"
OUT.mkdir(exist_ok=True)

res = run(verbose=False)

# ---------------------------------------------------------------- Chart 1
pm = res["payment_rates"].sort_values("return_rate_pct", ascending=False)
rates = pm["return_rate_pct"]
ratio = rates["COD"] / rates["CARD"]

fig, ax = plt.subplots(figsize=(8, 5))
colors = ["#B5452F" if m == "COD" else "#2E6B4F" for m in rates.index]
bars = ax.bar(rates.index, rates.values, color=colors)
for b, v in zip(bars, rates.values):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}%",
            ha="center", va="bottom", fontsize=12, fontweight="bold")
ax.set_title(f"COD Returns at {rates['COD']:.1f}% - {ratio:.1f}x Card", fontsize=14, fontweight="bold")
ax.set_xlabel("Payment method")
ax.set_ylabel("Return rate (%)")
ax.set_ylim(0, rates.max() * 1.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "return_rate_by_payment.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Chart 2
mc = res["monthly_clean"]
peak = res["true_peak"]
labels = [pd.Period(m).strftime("%b %Y") for m in mc.index]

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(labels, mc.values, marker="o", linewidth=2.5, color="#2E6B4F")
for x, y in zip(labels, mc.values):
    ax.annotate(f"{y:,.0f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=10)
peak_i = list(mc.index).index(peak)
ax.plot(labels[peak_i], mc[peak], marker="o", markersize=12, color="#E3A33B")
ax.set_title(f"Outlier-Corrected Monthly Revenue - Peak in {pd.Period(peak).strftime('%B %Y')} "
             f"(Rs {mc[peak]:,.2f})", fontsize=13, fontweight="bold")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (INR)")
ax.set_ylim(0, mc.max() * 1.15)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "monthly_revenue_trend.png", dpi=150)
plt.close(fig)

print("Saved:")
print(" ", (OUT / "return_rate_by_payment.png").relative_to(ROOT))
print(" ", (OUT / "monthly_revenue_trend.png").relative_to(ROOT))
