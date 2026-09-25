"""
Inspect BEFORE dropping: what exactly are the rows with a missing CustomerID?
Run this on the raw Online Retail II file (next to it). It DROPS NOTHING - it
only measures what a drop would discard, so your decision and your README are
evidence-based instead of blind.

Run:  python inspect_missing.py
"""

import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = ["online_retail_II.xlsx", "online_retail_II.csv",
              "Online Retail II.xlsx", "Online Retail.xlsx", "online_retail.csv"]


def find_source():
    for n in CANDIDATES:
        if (HERE / n).exists():
            return HERE / n
    raise SystemExit("dataset not found next to this script")


def load_raw(p: Path) -> pd.DataFrame:
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.concat(pd.read_excel(p, sheet_name=None).values(), ignore_index=True)
    try:
        return pd.read_csv(p, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding="ISO-8859-1")


df = load_raw(find_source())
df.columns = [c.strip() for c in df.columns]
df = df.rename(columns={"InvoiceNo": "Invoice", "UnitPrice": "Price", "Customer ID": "CustomerID"})
df["Revenue"] = df["Quantity"] * df["Price"]

miss = df["CustomerID"].isna()
total_rev = df["Revenue"].sum()

print(f"Total rows              : {len(df):,}")
print(f"Rows missing CustomerID : {miss.sum():,}  ({miss.mean()*100:.1f}% of rows)")
print(f"Revenue in missing rows : {df.loc[miss, 'Revenue'].sum():,.0f}  "
      f"({df.loc[miss, 'Revenue'].sum()/total_rev*100:.1f}% of all revenue)")

print("\nMissing-CustomerID rows by country (top 5):")
print(df.loc[miss, "Country"].value_counts().head())

d = pd.to_datetime(df.loc[miss, "InvoiceDate"], errors="coerce")
print(f"\nDate range of missing rows: {d.min()}  ->  {d.max()}")
print("(If they cluster in one period/country, the missingness is systematic —")
print(" worth a sentence in your README. If spread out, it's likely just anonymous sales.)")
