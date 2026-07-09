# RBA Exchange Rates Clean (2014–2017)

Clean the official RBA historical workbook **Exchange Rates – Daily – 2014 to 2017** into a load-ready CSV.

## Output file

**`rba_exchange_rates_clean.csv`**

| Rule | Detail |
|------|--------|
| Header | First row only |
| Date column | `rate_date` as `YYYY-MM-DD` |
| Rate columns | RBA Series IDs (`FXRUSD`, `FXRTWI`, …) — all series preserved |
| Rows | One business day each |
| Missing values | Blank (not invented) |
| Metadata removed | Title, Description, Frequency, Type, Units, Source, Publication date, Series ID |

## Generate the CSV (recommended)

```bash
git clone https://github.com/ozzy2438/rba-exchange-rates-clean.git
cd rba-exchange-rates-clean

pip install pandas xlrd openpyxl

# downloads official XLS if not present, then writes the clean CSV
python clean_rba_xls.py

# or use your local attachment
python clean_rba_xls.py /path/to/2014-2017.xls
```

This creates **`rba_exchange_rates_clean.csv`** in the current directory (ready to open or download from your machine).

## Script download (direct)

- Cleaner script: https://raw.githubusercontent.com/ozzy2438/rba-exchange-rates-clean/main/clean_rba_xls.py  
- Repo: https://github.com/ozzy2438/rba-exchange-rates-clean  

## Official RBA source

- XLS: https://www.rba.gov.au/statistics/tables/xls-hist/2014-2017.xls  
- Historical tables: https://www.rba.gov.au/statistics/historical-data.html  

## Cleaning logic

1. Open first sheet with no assumed header  
2. Find the row where column A is `Series ID` (fallback: Excel row 11)  
3. Use Series IDs as column names; first column becomes `rate_date`  
4. Keep only rows whose first cell parses as a date  
5. Format dates as `YYYY-MM-DD`  
6. Coerce rate columns to numeric; empty → blank on write  
7. Drop report metadata rows  

## Attribution

Source data © Reserve Bank of Australia. Use subject to RBA copyright and disclaimer terms.
