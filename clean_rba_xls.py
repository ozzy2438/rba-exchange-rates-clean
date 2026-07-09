#!/usr/bin/env python3
"""
Clean RBA Exchange Rates – Daily – 2014 to 2017 (2014-2017.xls)
into rba_exchange_rates_clean.csv

Requirements:
  pip install pandas openpyxl xlrd

Usage:
  python clean_rba_xls.py [path/to/2014-2017.xls]

If no path is given, downloads the official file from RBA.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

RBA_URL = "https://www.rba.gov.au/statistics/tables/xls-hist/2014-2017.xls"
OUT_NAME = "rba_exchange_rates_clean.csv"

META_LABELS = {
    "title",
    "description",
    "frequency",
    "type",
    "units",
    "source",
    "publication date",
    "series id",
}


def load_raw(path: Path) -> pd.DataFrame:
    # xlrd for .xls; openpyxl for .xlsx
    engine = "xlrd" if path.suffix.lower() == ".xls" else None
    return pd.read_excel(path, sheet_name=0, header=None, dtype=object, engine=engine)


def find_series_id_row(raw: pd.DataFrame) -> int:
    for i, val in enumerate(raw.iloc[:, 0].astype(str).str.strip().str.lower()):
        if val == "series id":
            return i
    # Community parsers (e.g. muhashi/exchange-rates-rba) use range=10
    return 10


def parse_rate_date(x) -> pd.Timestamp:
    if pd.isna(x):
        return pd.NaT
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        # Excel serial date
        try:
            return pd.to_datetime(x, unit="D", origin="1899-12-30")
        except Exception:
            return pd.NaT
    return pd.to_datetime(x, dayfirst=True, errors="coerce")


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    series_row_idx = find_series_id_row(raw)
    headers = raw.iloc[series_row_idx].tolist()

    col_names = ["rate_date"]
    for j, h in enumerate(headers[1:], start=1):
        name = str(h).strip() if pd.notna(h) else ""
        if name in ("", "nan", "None"):
            name = f"col_{j}"
        col_names.append(name)

    data = raw.iloc[series_row_idx + 1 :].copy()
    data.columns = col_names

    data["rate_date"] = data["rate_date"].map(parse_rate_date)
    data = data.dropna(subset=["rate_date"])

    # Drop any leftover metadata-looking rows
    as_str = data["rate_date"].astype(str).str.lower()
    data = data[~as_str.isin(META_LABELS)]

    data["rate_date"] = data["rate_date"].dt.strftime("%Y-%m-%d")

    rate_cols = [c for c in data.columns if c != "rate_date"]
    for c in rate_cols:
        data[c] = pd.to_numeric(data[c], errors="coerce")

    # Drop fully empty columns; keep all series that have any data or were named
    data = data.dropna(axis=1, how="all")
    data = data.sort_values("rate_date").reset_index(drop=True)
    return data


def main() -> int:
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
        if not src.exists():
            print(f"File not found: {src}", file=sys.stderr)
            return 1
    else:
        src = Path("2014-2017.xls")
        if not src.exists():
            print(f"Downloading {RBA_URL} ...")
            urlretrieve(RBA_URL, src)

    print(f"Reading {src} ...")
    raw = load_raw(src)
    cleaned = clean(raw)

    out = Path(OUT_NAME)
    cleaned.to_csv(out, index=False, na_rep="")
    print(f"Wrote {len(cleaned)} rows × {len(cleaned.columns)} columns → {out.resolve()}")
    print("Columns:", list(cleaned.columns))
    print("Date range:", cleaned["rate_date"].iloc[0], "→", cleaned["rate_date"].iloc[-1])
    print("\nFirst 3 rows:")
    print(cleaned.head(3).to_string(index=False))
    print("\nLast 3 rows:")
    print(cleaned.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
