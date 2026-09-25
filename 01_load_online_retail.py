"""
E-commerce RFM Project - Step 1 (REAL DATA): Load & Clean Online Retail II
--------------------------------------------------------------------------
Source : "Online Retail II" - a real UK online retailer, Dec 2009 - Dec 2011.
         Free from the UCI Machine Learning Repository or Kaggle
         (search: "Online Retail II"). Download the file and put it NEXT TO
         this script. Works with the .xlsx (2 sheets) or the .csv version.

Why this replaces the dummyJSON version: dummyJSON gave every customer exactly
one order, so RFM's Frequency was dead. Online Retail II has real repeat buyers,
real dates, and real CustomerIDs -> all three of R, F, M become meaningful.

Output : 4 files in ./data/  (same names/columns as before, so 02_rfm_scoring.py
         runs UNCHANGED):
         dim_customer.csv, dim_product.csv, fact_order.csv, fact_order_line.csv

Before running:  pip install pandas openpyxl
Run:             python 01_load_online_retail.py
"""

import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)

# Common filenames people end up with after downloading. Put the file next to
# this script; the loader picks up whichever exists.
CANDIDATES = [
    "online_retail_II.xlsx", "online_retail_II.csv",
    "Online Retail II.xlsx", "Online Retail.xlsx", "online_retail.csv",
]


def find_source() -> Path:
    for name in CANDIDATES:
        p = HERE / name
        if p.exists():
            return p
    raise SystemExit(
        "Could not find the dataset. Download 'Online Retail II' (UCI or Kaggle),\n"
        f"put the file NEXT TO this script, and name it one of: {CANDIDATES}"
    )


def load_raw(path: Path) -> pd.DataFrame:
    """Read the file whether it's .xlsx (possibly 2 sheets) or .csv."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        sheets = pd.read_excel(path, sheet_name=None)   # dict: every sheet
        df = pd.concat(sheets.values(), ignore_index=True)
    else:
        try:
            df = pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="ISO-8859-1")   # original file needs latin-1
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Different releases name columns differently; map them to one standard set."""
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "InvoiceNo": "Invoice",
        "UnitPrice": "Price",
        "Customer ID": "CustomerID",
    })
    return df


def report(df: pd.DataFrame, label: str):
    print(f"\n[{label}]  rows: {len(df)}")
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        print("  OK - no missing values")
    else:
        for col, n in nulls.items():
            print(f"  ! {col}: {int(n)} missing ({n/len(df)*100:.1f}%)")


# --- 1. Load raw ---
src = find_source()
print(f"Loading: {src.name}")
df = normalize_columns(load_raw(src))
print(f"Raw rows: {len(df)}")
report(df, "raw")

# --- 2. Clean real-world dirt (each step is an evidence-based decision) ---
# These are the classic Online Retail data-quality issues. Document them in your
# README: this is the honest "what I removed and why" section.
print("\n=== Cleaning ===")

before = len(df)
df = df.dropna(subset=["CustomerID"])
print(f"  dropped {before - len(df)} rows with no CustomerID (can't attribute to a customer)")

before = len(df)
df = df[~df["Invoice"].astype(str).str.startswith("C")]
print(f"  dropped {before - len(df)} cancellation invoices (Invoice starts with 'C')")

before = len(df)
df = df[df["Quantity"] > 0]
print(f"  dropped {before - len(df)} rows with Quantity <= 0 (returns / corrections)")

before = len(df)
df = df[df["Price"] > 0]
print(f"  dropped {before - len(df)} rows with Price <= 0 (freebies / adjustments)")

before = len(df)
df = df.drop_duplicates()
print(f"  dropped {before - len(df)} exact duplicate rows (would inflate Frequency/Monetary)")

# Non-product StockCodes: postage, fees, manual adjustments, tests, etc.
# Matched two ways: a known list, plus 'code is all letters with no digit'
# (real product codes always contain a digit).
NON_PRODUCT = {"POST", "DOT", "M", "C2", "D", "S", "B", "BANK CHARGES", "ADJUST",
               "AMAZONFEE", "CRUK", "PADS", "DCGSSGIRL", "DCGSSBOY", "gift_0001"}
_code = df["StockCode"].astype(str).str.strip()
_is_non_product = _code.str.upper().isin({c.upper() for c in NON_PRODUCT}) | \
                  _code.str.fullmatch(r"[A-Za-z ]+")
before = len(df)
df = df[~_is_non_product]
print(f"  dropped {before - len(df)} non-product rows (postage, fees, manual, tests)")

# Types + a computed line amount
df["CustomerID"] = df["CustomerID"].astype(int)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["LineAmount"] = df["Quantity"] * df["Price"]
print(f"  clean rows remaining: {len(df)}")

# --- 3. fact_order  (ONE row per invoice = one order) -> RFM basis ---
# Column names match the old fact_order so 02_rfm_scoring.py needs no changes.
fact_order = (
    df.groupby("Invoice")
      .agg(CustomerID=("CustomerID", "first"),
           OrderDate=("InvoiceDate", "min"),
           Amount=("LineAmount", "sum"))
      .reset_index()
      .rename(columns={"Invoice": "OrderID"})
)

# --- 4. fact_order_line  (ONE row per invoice line) -> product/category analysis ---
fact_order_line = (
    df[["Invoice", "StockCode", "Quantity", "Price", "LineAmount"]]
      .rename(columns={"Invoice": "OrderID", "StockCode": "ProductID"})
)

# --- 5. dim_customer ---
dim_customer = (
    df.groupby("CustomerID")
      .agg(Country=("Country", "first"))
      .reset_index()
)

# --- 6. dim_product ---
dim_product = (
    df.groupby("StockCode")
      .agg(ProductName=("Description", "first"),
           Price=("Price", "median"))
      .reset_index()
      .rename(columns={"StockCode": "ProductID"})
)

# --- 7. Save ---
dim_customer.to_csv(OUT / "dim_customer.csv", index=False, encoding="utf-8-sig")
dim_product.to_csv(OUT / "dim_product.csv", index=False, encoding="utf-8-sig")
fact_order.to_csv(OUT / "fact_order.csv", index=False, encoding="utf-8-sig")
fact_order_line.to_csv(OUT / "fact_order_line.csv", index=False, encoding="utf-8-sig")

# --- 8. Quick sanity check: is Frequency actually varied now? ---
freq = fact_order.groupby("CustomerID")["OrderID"].nunique()
print("\nDone. Files written to './data/'.")
print(f"  fact_order      : {len(fact_order):>6} rows  (orders/invoices)")
print(f"  fact_order_line : {len(fact_order_line):>6} rows")
print(f"  dim_customer    : {len(dim_customer):>6} rows  (customers)")
print(f"  dim_product     : {len(dim_product):>6} rows")
print(f"\n  Orders per customer -> min {freq.min()}, median {int(freq.median())}, max {freq.max()}")
print("  (If max > 1, Frequency is real and RFM will be meaningful.)")
