"""
E-commerce RFM Project - Step 2: RFM Scoring (pandas)
-----------------------------------------------------
Input  : ./data/fact_order.csv        (produced by 01_extract_and_clean.py)
Output : ./data/dim_customer_rfm.csv  (one row per customer + R/F/M scores + segment)

RFM in plain terms, per customer:
  Recency   = how many days since their LAST order   (smaller = better / more recent)
  Frequency = how many orders they placed            (bigger  = better)
  Monetary  = how much they spent in total           (bigger  = better)
Each is scored 1-5 (quintiles). The scores combine into an actionable segment
label ("Champions", "At Risk", ...) that drives the dashboard.

Run:  python 02_rfm_scoring.py
"""

import pandas as pd
from pathlib import Path

# 'data' folder lives NEXT TO this script, regardless of where you run it from.
DATA = Path(__file__).resolve().parent / "data"

# --- 1. Load the order fact table ---
order_file = DATA / "fact_order.csv"
if not order_file.exists():
    raise SystemExit(
        f"Could not find {order_file}\n"
        "-> Run 01_extract_and_clean.py FIRST (it creates the 'data' folder),\n"
        "   and keep BOTH scripts in the SAME folder."
    )
fact = pd.read_csv(order_file, parse_dates=["OrderDate"])

# --- 2. Snapshot date = the day AFTER the most recent order ---
# Recency is measured against this point, so the newest order gets Recency = 1, not 0.
snapshot = fact["OrderDate"].max() + pd.Timedelta(days=1)

# --- 3. Build raw R, F, M values per customer ---
rfm = fact.groupby("CustomerID").agg(
    Recency=("OrderDate", lambda s: (snapshot - s.max()).days),
    Frequency=("OrderID", "nunique"),
    Monetary=("Amount", "sum"),
).reset_index()

# --- 4. Turn each raw value into a 1-5 score (quintiles) ---
# rank(method="first") breaks ties so qcut can always form 5 equal groups, even
# when many customers share the same value (common with small data). Without it,
# qcut can crash with a "bin edges are not unique" error.
def score(series, reverse=False):
    ranked = series.rank(method="first")
    labels = [5, 4, 3, 2, 1] if reverse else [1, 2, 3, 4, 5]
    return pd.qcut(ranked, 5, labels=labels).astype(int)

rfm["R"] = score(rfm["Recency"], reverse=True)  # most recent -> 5
rfm["F"] = score(rfm["Frequency"])              # most orders -> 5
rfm["M"] = score(rfm["Monetary"])               # most spend  -> 5

# --- 5. Combine into a segment label ---
# Collapse F and M into one "value" score (their average), then read the segment
# off a simple Recency x Value grid. Every (R, FM) combination lands somewhere.
rfm["FM"] = ((rfm["F"] + rfm["M"]) / 2).round().astype(int)

def segment(r, fm):
    if r >= 4 and fm >= 4: return "Champions"           # recent + high value
    if r >= 3 and fm >= 3: return "Loyal"               # solid all round
    if r >= 4 and fm <= 2: return "New / Promising"     # just arrived, low spend so far
    if r <= 2 and fm >= 4: return "At Risk"             # was valuable, gone quiet
    if r <= 2 and fm <= 2: return "Lost / Hibernating"  # gone and low value
    return "Needs Attention"                            # everything in between

rfm["Segment"] = [segment(r, fm) for r, fm in zip(rfm["R"], rfm["FM"])]

# --- 6. Save ---
rfm.to_csv(DATA / "dim_customer_rfm.csv", index=False, encoding="utf-8-sig")

print("Done -> data/dim_customer_rfm.csv")
print(f"Customers scored: {len(rfm)}")
print("\nSegment distribution:")
print(rfm["Segment"].value_counts())
