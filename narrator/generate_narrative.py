"""
narrator/generate_narrative.py  |  Part 3 (Tasks 2-5)  |  Mamaearth Returns Pipeline

Reads narrator/findings.json (written by analysis/clean_and_eda.py) and turns it
into an SCR (Situation - Complication - Resolution) business narrative.

  * Online path : Gemini via the google-genai library, if GEMINI_API_KEY is set.
  * Offline path: deterministic f-string template, needs no key and no network.

Run from the repo root:   python narrator/generate_narrative.py
The narrative is printed, checked for the 5 key figures, and saved to
narrator/sample_output.txt.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINDINGS_PATH = HERE / "findings.json"
SAMPLE_PATH = HERE / "sample_output.txt"

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

SYSTEM_INSTRUCTION = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Write a concise business narrative of about 250 words in exactly three labeled sections, "
    "in this order: 'Situation:', 'Complication:', 'Resolution:'. "
    "STRICT RULE: every number in your output must come from the supplied findings and must "
    "appear with exactly the same value and decimals as given (e.g. 97,358.30, 44.4%). "
    "Do not invent, estimate, round differently or derive any new statistic. "
    "Name the peak month by its month name (e.g. March). Use plain business English. "
    "Output ONLY the final narrative: no preamble, no notes, and no list checking the numbers."
)


def _month_name(yyyy_mm: str) -> str:
    import calendar
    year, month = yyyy_mm.split("-")
    return f"{calendar.month_name[int(month)]} {year}"


def build_user_prompt(findings: dict) -> str:
    """Prompt is built from the findings dict -- no numbers are hardcoded here."""
    r = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    return (
        "Write the SCR narrative using ONLY these verified findings:\n"
        f"- Cleaned total revenue: INR {findings['cleaned_total_revenue_inr']:,.2f} "
        f"(raw total before cleaning: INR {findings['raw_total_revenue_inr']:,.2f})\n"
        f"- Difference caused entirely by duplicate (double-submitted) orders: "
        f"INR {findings['duplicate_reconciliation_delta_inr']:,.2f}\n"
        f"- Return rate by payment method: COD {r['COD']}%, UPI {r['UPI']}%, CARD {r['CARD']}%\n"
        f"- Highest-risk segment: {seg['payment_method']} orders in Tier-{seg['city_tier']} cities "
        f"at {seg['return_rate_pct']}% return rate\n"
        f"- True peak revenue month: {_month_name(peak['month'])} at INR {peak['revenue_inr']:,.2f}\n"
        f"- {_month_name(infl['month'])} looked highest at INR {infl['apparent_revenue_inr']:,.2f} "
        f"only because of two bulk outlier orders; corrected it is INR "
        f"{infl['corrected_revenue_inr']:,.2f}\n"
        "Mention the cleaned total revenue, the COD return rate, the highest-risk segment rate, "
        "the duplicate delta, and the true peak month with its revenue."
    )


def generate_scr_narrative_offline(findings: dict) -> dict:
    """Task 4: deterministic template. No API key, no network, same return shape."""
    r = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]
    narrative = (
        "Situation:\n"
        f"After cleaning, Mamaearth's order book for Jan-Jun 2026 totals INR "
        f"{findings['cleaned_total_revenue_inr']:,.2f}. The raw system figure of INR "
        f"{findings['raw_total_revenue_inr']:,.2f} was overstated by INR "
        f"{findings['duplicate_reconciliation_delta_inr']:,.2f}, entirely due to double-submitted "
        "duplicate orders.\n\n"
        "Complication:\n"
        f"Returns are concentrated in Cash-on-Delivery. COD orders are returned at {r['COD']}%, "
        f"against {r['UPI']}% for UPI and {r['CARD']}% for Card. The blended COD rate hides the real "
        f"hotspot: {seg['payment_method']} orders in Tier-{seg['city_tier']} cities return at "
        f"{seg['return_rate_pct']}%. Revenue reporting is also distorted: "
        f"{_month_name(infl['month'])} appeared to be the best month at INR "
        f"{infl['apparent_revenue_inr']:,.2f}, but only because of two bulk outlier orders; "
        f"corrected, it is INR {infl['corrected_revenue_inr']:,.2f}.\n\n"
        "Resolution:\n"
        f"1) Target {seg['payment_method']} in Tier-{seg['city_tier']} cities first: add order "
        "confirmation calls, prepaid incentives or a COD fee.\n"
        "2) Fix the double-submit bug and de-duplicate orders before any revenue reporting.\n"
        "3) Flag bulk orders in dashboards so they do not distort trends. The true peak month is "
        f"{_month_name(peak['month'])} at INR {peak['revenue_inr']:,.2f}; use it as the benchmark "
        "for planning."
    )
    return {"status": "success", "narrative": narrative, "tokens": 0, "source": "offline"}


def generate_scr_narrative(findings: dict) -> dict:
    """Task 2 + 3: Gemini call. Never raises; always returns a dict."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"status": "error", "narrative": None, "message": "No GEMINI_API_KEY set"}
    try:
        from google import genai
        from google.genai import types

        # timeout is in MILLISECONDS in HttpOptions: 30000 ms = 30 s (>= 10 s minimum)
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))
        response = client.models.generate_content(
            model=MODEL,
            contents=build_user_prompt(findings),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                # temperature 0.0 = deterministic: this is a factual business report, not
                # creative writing, so we want the same, number-faithful output every run.
                temperature=0.0,
                # explicit limit (not API default). Newer Gemini models spend part of this
                # budget on internal reasoning, so 8192 leaves room for that plus a full
                # 3-section ~250-word narrative without it being cut off.
                max_output_tokens=8192,
            ),
        )
        text = (response.text or "").strip()

        # Reject cut-off or malformed answers so a broken narrative is never returned
        cand = response.candidates[0] if getattr(response, "candidates", None) else None
        finish = str(getattr(cand, "finish_reason", "") or "")
        if "MAX_TOKENS" in finish:
            raise ValueError("Gemini output was cut off at max_output_tokens")
        missing = [s for s in ("Situation", "Complication", "Resolution") if s not in text]
        if missing:
            raise ValueError(f"Gemini output missing SCR section(s): {missing}")

        usage = getattr(response, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", None) if usage else None
        return {"status": "success", "narrative": text, "tokens": tokens, "source": f"gemini:{MODEL}"}
    except Exception as err:  # caller never receives a raw exception
        return {"status": "error", "narrative": None, "message": str(err)}


def get_narrative(findings: dict) -> dict:
    """Try Gemini; on missing key or any error, fall back to the offline template."""
    result = generate_scr_narrative(findings)
    if result["status"] != "success":
        print(f"[info] Online path unavailable ({result.get('message')}). Using offline fallback.")
        result = generate_scr_narrative_offline(findings)
    return result


def check_figures(narrative: str, findings: dict) -> bool:
    """Task 5: confirm the 5 key figures appear in the narrative (commas ignored)."""
    text = narrative.replace(",", "")

    def num(x):  # 97358.3 -> accept "97358.3" (also matches "97358.30")
        return f"{x:.2f}".rstrip("0").rstrip(".")

    peak = findings["true_peak_month"]
    month = _month_name(peak["month"]).split()[0]
    checks = [
        ("Cleaned total revenue", [num(findings["cleaned_total_revenue_inr"])]),
        ("COD return rate", [num(findings["return_rate_by_payment"]["COD"])]),
        ("Highest-risk segment rate", [num(findings["highest_risk_segment"]["return_rate_pct"])]),
        ("Duplicate reconciliation delta", [num(findings["duplicate_reconciliation_delta_inr"])]),
        ("True peak month + revenue", [month, num(peak["revenue_inr"])]),
    ]
    all_ok = True
    print("\nNUMERIC ACCURACY CHECK")
    for label, needles in checks:
        ok = all(n in text for n in needles)
        all_ok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {' + '.join(needles)}")
    print(f"  RESULT: {'ALL 5 PASS' if all_ok else 'FAILED'}")
    return all_ok


if __name__ == "__main__":
    with open(FINDINGS_PATH, encoding="utf-8") as f:
        findings = json.load(f)

    result = get_narrative(findings)
    print(f"\nSource: {result['source']} | tokens: {result['tokens']}\n")
    print(result["narrative"])
    passed = check_figures(result["narrative"], findings)

    with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
        f.write(f"Source: {result['source']} | tokens: {result['tokens']}\n\n")
        f.write(result["narrative"] + "\n")
    print(f"\nSaved narrative to narrator/{SAMPLE_PATH.name}")

    # Also run the checker on the SAVED file (what the grader verifies)
    print("\nRe-checking saved sample_output.txt:")
    check_figures(SAMPLE_PATH.read_text(encoding="utf-8"), findings)
