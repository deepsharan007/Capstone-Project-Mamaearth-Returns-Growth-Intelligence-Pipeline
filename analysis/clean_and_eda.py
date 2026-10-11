"""
analysis/clean_and_eda.py  |  Part 2 (Tasks 1-10)  |  Mamaearth Returns Pipeline

Independent pandas pipeline over the RAW CSVs in data/ (does not use the SQL DB).
Run from the repo root:   python analysis/clean_and_eda.py

Order matters:
  dedupe (Task 3) BEFORE imputing (Task 4)  -> median is computed on real orders only
  outliers (Task 6) BEFORE monthly trend (Task 10) -> trend can be outlier-corrected

At the end it writes narrator/findings.json (Part 3, Task 1) from the computed
values -- never hand-typed.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FINDINGS_PATH = ROOT / "narrator" / "findings.json"

KEY_COLS = ["customer_id", "product_id", "order_date", "quantity",
            "discount_pct", "payment_method", "rating", "returned"]


def band(r):
    """Taught correlation-strength bands on |r|."""
    a = abs(r)
    if a < 0.2:
        return "negligible"
    if a < 0.4:
        return "weak"
    if a < 0.7:
        return "moderate"
    return "strong"


def run(verbose=True):
    say = print if verbose else (lambda *a, **k: None)

    def header(t):
        say("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)

    # ------------------------------------------------------------------ Task 1
    header("TASK 1 - Load and inspect")
    customers = pd.read_csv(DATA / "customers.csv")
    products = pd.read_csv(DATA / "products.csv")
    orders = pd.read_csv(DATA / "orders.csv")
    say("customers.shape:", customers.shape)
    say("products.shape :", products.shape)
    say("orders.shape   :", orders.shape, " (raw, before any cleaning)")
    # Raw total, recomputed here from the raw CSV exactly like Part 1 Report (a)
    # (NULL discount treated as 0%) so it is never hand-typed.
    _raw = orders.merge(products, on="product_id", how="left")
    raw_total = round((_raw["quantity"] * _raw["price"] * (1 - _raw["discount_pct"].fillna(0) / 100)).sum(), 2)
    say(f"Raw total revenue (180 rows, same formula as SQL Report a): {raw_total:,.2f}")
    say("\nMissing values in raw orders:\n" + orders.isnull().sum().to_string())

    # ------------------------------------------------------------------ Task 2
    header("TASK 2 - Standardise payment_method casing")
    raw_vals = orders["payment_method"].unique()
    say(f"Before: {len(raw_vals)} distinct values -> {list(raw_vals)}")
    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    clean_vals = orders["payment_method"].unique()
    say(f"After : {len(clean_vals)} distinct values -> {list(clean_vals)}")
    say("Counts after fix:\n" + orders["payment_method"].value_counts().to_string())

    # ------------------------------------------------------------------ Task 3
    header("TASK 3 - Remove duplicate orders (natural key = all columns except order_id)")
    dup_mask = orders.duplicated(subset=KEY_COLS, keep="first")
    dropped = orders[dup_mask].copy()
    say(f"Duplicate rows flagged: {int(dup_mask.sum())}")
    say("Dropped order_ids:", ", ".join(dropped["order_id"]))
    orders_clean = orders[~dup_mask].copy()
    say("orders_clean.shape:", orders_clean.shape)

    # ------------------------------------------------------------------ Task 4
    header("TASK 4 - Impute missing values (on the deduplicated frame)")
    n_disc = int(orders_clean["discount_pct"].isnull().sum())
    n_rate = int(orders_clean["rating"].isnull().sum())
    say(f"discount_pct missing: {n_disc} rows -> fill with 0 (no promo code applied)")
    orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
    rating_median = orders_clean["rating"].median()
    say(f"rating median (non-null, deduplicated): {rating_median}")
    say(f"rating missing: {n_rate} rows -> fill with median {rating_median}")
    orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)
    say("Nulls after imputing:", orders_clean[["discount_pct", "rating"]].isnull().sum().to_dict())

    # ------------------------------------------------------------------ Task 5
    header("TASK 5 - Merge and reconcile against Part 1")
    df = (orders_clean
          .merge(products, on="product_id", how="left")
          .merge(customers, on="customer_id", how="left"))
    df["order_value"] = df["quantity"] * df["price"] * (1 - df["discount_pct"] / 100)
    clean_total = round(df["order_value"].sum(), 2)
    say(f"Merged frame shape: {df.shape}")
    say(f"Cleaned total order_value ({len(df)} rows): {clean_total:,.2f}")

    # Independent check: value of the 5 dropped duplicates
    dropped["discount_pct"] = dropped["discount_pct"].fillna(0)
    dropped = dropped.merge(products, on="product_id", how="left")
    dropped["order_value"] = dropped["quantity"] * dropped["price"] * (1 - dropped["discount_pct"] / 100)
    dup_value = round(dropped["order_value"].sum(), 2)
    delta = round(raw_total - clean_total, 2)
    say("\nDropped duplicates and their order_value:")
    say(dropped[["order_id", "quantity", "price", "discount_pct", "order_value"]].round(2).to_string(index=False))
    say(f"Sum of dropped duplicates' order_value: {dup_value:,.2f}")
    say(f"Part 1 raw total - Part 2 cleaned total: {raw_total:,.2f} - {clean_total:,.2f} = {delta:,.2f}")
    say(f"Delta fully explained by duplicates: {abs(delta - dup_value) < 0.01}")
    say(
        "\nRECONCILIATION NOTE: Part 1 Report (a) totals Rs {:,.2f} over 180 raw rows; this cleaned "
        "pipeline totals Rs {:,.2f} over 175 rows, a difference of Rs {:,.2f}. The entire difference is "
        "the 5 double-submitted orders removed in Task 3 ({}), whose combined order_value is exactly "
        "Rs {:,.2f}. The Task 4 imputation does not move the total: SQL already treated NULL discount as "
        "0% via COALESCE (the same as our fillna(0)), and rating is not part of the revenue formula."
        .format(raw_total, clean_total, delta, ", ".join(dropped["order_id"]), dup_value)
    )

    # ------------------------------------------------------------------ Task 6
    header("TASK 6 - IQR outlier detection on quantity (flag, do not drop)")
    q1 = df["quantity"].quantile(0.25)
    q3 = df["quantity"].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    say(f"Q1 = {q1}, Q3 = {q3}, IQR = {iqr}, lower = {lower}, upper = {upper}")
    df["is_outlier"] = (df["quantity"] < lower) | (df["quantity"] > upper)
    outliers = df[df["is_outlier"]]
    say(f"Outlier rows: {len(outliers)} (kept in dataset, flagged is_outlier=True)")
    say(outliers[["order_id", "customer_id", "order_date", "quantity", "order_value"]].round(2).to_string(index=False))

    # ------------------------------------------------------------------ Task 7
    header("TASK 7 - Hypothesis: COD orders have a higher return rate")
    say("H1: Cash-on-Delivery (COD) orders are returned more often than prepaid (CARD/UPI) orders.")
    pm = df.groupby("payment_method")["returned"].agg(["count", "mean"])
    pm["return_rate_pct"] = (pm["mean"] * 100).round(1)
    pm = pm.sort_values("return_rate_pct", ascending=False)
    say(pm.to_string())
    rates = pm["return_rate_pct"].to_dict()
    cod_highest = rates["COD"] == max(rates.values())
    verdict7 = "Confirmed" if cod_highest else "Busted"
    say(f"Verdict: {verdict7} - COD return rate {rates['COD']}% vs CARD {rates['CARD']}% "
        f"and UPI {rates['UPI']}% ({rates['COD'] / rates['CARD']:.1f}x Card).")

    # ------------------------------------------------------------------ Task 8
    header("TASK 8 - Multi-level segmentation: payment_method x city_tier")
    seg = df.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
    seg["return_rate_pct"] = (seg["mean"] * 100).round(1)
    seg = seg.sort_values("return_rate_pct", ascending=False)
    say(seg.to_string())
    (top_pm, top_tier) = seg.index[0]
    top = seg.iloc[0]
    say(f"\nHIGHEST-RISK SEGMENT: {top_pm} + Tier-{top_tier} cities at {top['return_rate_pct']}% "
        f"({int(top['count'])} orders).")
    cod_t1 = seg.loc[("COD", 1)]
    cod_t2 = seg.loc[("COD", 2)]
    say(f"COD is not uniform: Tier-1 COD {int(cod_t1['count'])} orders at {cod_t1['return_rate_pct']}% vs "
        f"Tier-2 COD {int(cod_t2['count'])} orders at {cod_t2['return_rate_pct']}%. The blended COD "
        f"rate of {rates['COD']}% hides that the problem is concentrated in Tier-2 cities.")

    # ------------------------------------------------------------------ Task 9
    header("TASK 9 - Correlation analysis")
    cols = ["rating", "returned", "discount_pct", "quantity"]
    corr = df[cols].corr()
    say(corr.round(3).to_string())
    say("\nBands: negligible 0-0.19 | weak 0.2-0.39 | moderate 0.4-0.69 | strong 0.7-1.0")
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            say(f"  {cols[i]:>12} vs {cols[j]:<12} r = {r:+.3f} -> {band(r)}")
    r_dr = corr.loc["discount_pct", "returned"]
    verdict9 = "Busted" if band(r_dr) == "negligible" else "Not busted"
    say(f"\nHypothesis 'higher discounts reduce returns': {verdict9} "
        f"(discount_pct vs returned r = {r_dr:+.2f}, {band(r_dr)}).")

    # ----------------------------------------------------------------- Task 10
    header("TASK 10 - Outlier-corrected monthly revenue")
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    monthly_all = df.groupby("month")["order_value"].sum().round(2)
    monthly_clean = df[~df["is_outlier"]].groupby("month")["order_value"].sum().round(2)
    say("(1) Including outliers:\n" + monthly_all.map("{:,.2f}".format).to_string())
    say("\n(2) Excluding outliers (corrected):\n" + monthly_clean.map("{:,.2f}".format).to_string())
    apparent_peak = monthly_all.idxmax()
    true_peak = monthly_clean.idxmax()
    out_desc = ", ".join(f"{r.order_id} on {r.order_date}" for r in outliers.itertuples())
    peak_name = pd.Period(true_peak).strftime("%B %Y")
    say(f"\nApparent peak (with outliers): {apparent_peak} at {monthly_all[apparent_peak]:,.2f}")
    say(f"True peak (outliers excluded): {true_peak} at {monthly_clean[true_peak]:,.2f}")
    say(f"{pd.Period(apparent_peak).strftime('%B')}'s apparent lead is an artifact of the two bulk orders "
        f"landing in that month ({out_desc}). Once they are excluded, "
        f"{apparent_peak} falls to {monthly_clean[apparent_peak]:,.2f} and {peak_name} is the genuine peak.")

    # ------------------------------------------------- findings.json (Part 3 T1)
    findings = {
        "cleaned_total_revenue_inr": clean_total,
        "raw_total_revenue_inr": raw_total,
        "duplicate_reconciliation_delta_inr": dup_value,
        "return_rate_by_payment": {k: float(rates[k]) for k in ["COD", "CARD", "UPI"]},
        "highest_risk_segment": {
            "payment_method": top_pm,
            "city_tier": int(top_tier),
            "return_rate_pct": float(top["return_rate_pct"]),
        },
        "true_peak_month": {"month": true_peak, "revenue_inr": float(monthly_clean[true_peak])},
        "outlier_inflated_month": {
            "month": apparent_peak,
            "apparent_revenue_inr": float(monthly_all[apparent_peak]),
            "corrected_revenue_inr": float(monthly_clean[apparent_peak]),
        },
    }

    return {
        "df": df,
        "payment_rates": pm,
        "monthly_all": monthly_all,
        "monthly_clean": monthly_clean,
        "true_peak": true_peak,
        "findings": findings,
    }


if __name__ == "__main__":
    res = run(verbose=True)
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(res["findings"], f, indent=2)
    print("\n" + "=" * 70)
    print(f"Wrote {FINDINGS_PATH.relative_to(ROOT)}:")
    print(json.dumps(res["findings"], indent=2))
