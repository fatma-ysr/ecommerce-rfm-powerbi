"""
Data audit (just in case): find EXACT DUPLICATE rows and NON-PRODUCT rows in the
raw Online Retail II file. Counts and shows them; removes NOTHING. Run this to
decide, with eyes open, what to strip before RFM.

Why these two matter:
  - Duplicate rows   -> inflate Frequency & Monetary, distorting RFM directly.
  - Non-product rows -> StockCodes like POST, DOT, M, BANK CHARGES, AMAZONFEE,
                        gift vouchers, tests. Not real purchases; they pollute
                        Monetary and any product/category analysis.

Run:  python audit_data.py
"""

import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = ["online_retail_II.xlsx", "online_retail_II.csv",
              "Online Retail II.xlsx", "Online Retail.xlsx", "online_retail.csv"]

# StockCodes that are NOT real products. Matched two ways: exact codes, and a
# rule for "all letters, no digit" (real product codes always contain digits).
NON_PRODUCT_CODES = {"POST", "DOT", "M", "C2", "BANK CHARGES", "AMAZONFEE",
                     "S", "CRUK", "PADS", "B", "gift_0001"}


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
total_rev = df["Revenue"].sum()

print(f"Total rows: {len(df):,}\n")

# --- 1. Exact duplicate rows ---
dup_mask = df.duplicated(keep="first")
print("=== Exact duplicate rows ===")
print(f"  count: {dup_mask.sum():,}  ({dup_mask.mean()*100:.2f}% of rows)")
print("  -> these are fully identical repeat rows; keeping one copy each is standard.")

# --- 2. Non-product rows ---
code = df["StockCode"].astype(str).str.strip()
is_listed = code.str.upper().isin({c.upper() for c in NON_PRODUCT_CODES})
is_all_letters = code.str.fullmatch(r"[A-Za-z ]+")     # no digit at all = not a product code
non_product = is_listed | is_all_letters

print("\n=== Non-product rows (postage, fees, manual, tests...) ===")
print(f"  count: {non_product.sum():,}  ({non_product.mean()*100:.2f}% of rows)")
print(f"  revenue: {df.loc[non_product, 'Revenue'].sum():,.0f} "
      f"({df.loc[non_product, 'Revenue'].sum()/total_rev*100:.2f}% of total)")
print("  StockCodes flagged (top 15):")
print(code[non_product].value_counts().head(15).to_string())

print("\n(Nothing removed. If these counts look right, the cleaning step will drop"
      "\n duplicates and non-product rows; tell me and I'll wire it into 01.)")
