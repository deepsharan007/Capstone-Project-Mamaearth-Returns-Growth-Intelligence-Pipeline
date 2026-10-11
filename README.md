# Mamaearth Returns & Growth Intelligence Pipeline

Capstone project, Data Analytics with AI & Gen AI, E&ICT Academy IIT Roorkee.

**Business question:** Where are returns really coming from, and what is the true revenue picture once the data is cleaned?

This repo has three connected layers. Each layer only reports numbers it computed itself or received from the layer before it:

```
data/*.csv  ──►  1. SQL layer (sql/)  ──►  2. Python layer (analysis/)  ──►  3. GenAI layer (narrator/)
  raw data        schema + 9 reports        cleaning, EDA, charts           SCR narrative (Gemini
                  on raw data               + writes findings.json          or offline fallback)
```

## Repository structure

```
<repo>/
├── README.md
├── requirements.txt              Python libraries
├── sql/
│   ├── schema.sql                Part 1 Task 1: creates customers, products, orders
│   ├── seed_data.sql             Part 1 Task 2: loads the 3 CSVs (blank cells -> NULL)
│   └── reports.sql               Part 1 Task 3: reports a-i, outputs pasted as comments
├── data/
│   ├── customers.csv             45 rows  (committed exactly as given, never edited)
│   ├── products.csv              16 rows
│   └── orders.csv                180 rows (deliberately messy)
├── analysis/
│   ├── clean_and_eda.py          Part 2 Tasks 1-10, and writes narrator/findings.json
│   └── visualize.py              Part 2 Task 11: saves the 2 charts
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json             verified figures, written by code (never hand-typed)
    ├── generate_narrative.py     Part 3: Gemini SCR narrative + offline fallback + checker
    └── sample_output.txt         saved narrative that the accuracy checker verifies
```

## How to reproduce every number (run in this order)

### Step 1: SQL layer (SQLite)

Use any SQLite tool, for example the `sqlite3` command line, DB Browser for SQLite, or sqliteonline.com.

```bash
sqlite3 mamaearth.db < sql/schema.sql      # create the 3 tables
sqlite3 mamaearth.db < sql/seed_data.sql   # load data; prints 45 / 16 / 180
sqlite3 mamaearth.db < sql/reports.sql     # run reports a-i
```

- Every query's expected output is pasted as a comment directly above it in `reports.sql`.
- `seed_data.sql` can be re-run safely, because it empties the tables first.
- Report (i) runs `ALTER TABLE`, so re-run `schema.sql` and `seed_data.sql` before running `reports.sql` a second time.

Key results:
- Report (a): 180 orders, raw revenue INR 99,860.20, average order value 554.78.
- Report (d): Jaipur 42.1%, Lucknow 30.6%, Bangalore 24.2%.

### Step 2: Python layer (pandas + Matplotlib)

```bash
pip install -r requirements.txt
python analysis/clean_and_eda.py     # prints every task result; writes narrator/findings.json
python analysis/visualize.py         # writes the 2 PNGs to visualizations/
```

Part 2 reads the raw CSVs directly, not the SQL database, so Step 1 and Step 2 can run in either order. At the end, `clean_and_eda.py` writes **`narrator/findings.json`**. This is how Part 2's verified numbers flow into Part 3.

Key results:
- **Cleaning:** 5 duplicates dropped (O0176–O0180), leaving 175 rows.
- **Revenue:** the cleaned total is INR 97,358.30. The INR 2,501.90 gap against SQL Report (a) is exactly the 5 duplicates.
- **Returns:** the COD return rate is 44.4%, against UPI 18.9% and Card 14.7%. The highest-risk segment is **COD in Tier-2 cities at 54.5%**.
- **Trend:** January only looked like the peak because of two bulk outlier orders. The true peak month is **March, at INR 20,318.90**.

### Step 3: GenAI layer (Gemini, or offline)

```bash
python narrator/generate_narrative.py
```

**Option A: no API key (offline path).** Just run the command above. It uses a deterministic template, so it needs no key, no network and no configuration.

**Option B: with Gemini.** Get a free key from Google AI Studio (https://aistudio.google.com/apikey) and set it as an environment variable. Never put the key in the code or commit it to the repo.

```bash
# macOS / Linux
export GEMINI_API_KEY="your-key-here"
# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"

python narrator/generate_narrative.py
```

If the key is missing or the API call fails for any reason, the script automatically falls back to the offline template.

The script does three things:
- Prints the Situation, Complication and Resolution narrative.
- Runs the 5-figure accuracy checker, which prints PASS or FAIL for each figure.
- Saves the narrative to `narrator/sample_output.txt` and re-checks the saved file.

The committed `sample_output.txt` comes from a real Gemini run. Its first line records the source and token count.

Gemini settings, and why each was chosen:

| Setting | Value | Why |
|---|---|---|
| System instruction | Analyst role, 3 labeled sections, no invented numbers | Kept separate from the user prompt |
| User prompt | Built from `findings.json` | No numbers hardcoded |
| `temperature` | `0.0` | Deterministic, factual report |
| `max_output_tokens` | `2048` | Explicit limit, so the narrative isn't cut off |
| Timeout | `30000` ms (30 s) | `HttpOptions` timeout is in milliseconds |
| Error handling | `try/except` | Always returns a status dict, never a raw exception |
