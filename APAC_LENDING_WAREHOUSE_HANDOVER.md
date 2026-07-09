# APAC Lending Warehouse — Project Handover

**Project:** APAC SME Lending Analytics Warehouse
**Platform:** Snowflake
**Status:** Complete — all layers built and validated
**Handover date:** 2026-07-09

---

## 1. Project Purpose

Analytics Engineering build for an SME lending / fintech-style portfolio. The project delivers an end-to-end Snowflake pipeline that takes raw source files (Lending Club loans, Australian Bureau of Statistics datasets, Reserve Bank of Australia exchange rates) through cleaning, dimensional modelling, and FX enrichment to dashboard-ready monthly marts that combine portfolio performance with Australian macroeconomic context.

## 2. Architecture

```
RAW  →  STAGING  →  DWH (DIM / FACT)  →  MART
```

| Layer | Database / Schema | Role |
|---|---|---|
| RAW | `APAC_LENDING_RAW` | Source files loaded as-is (all VARCHAR, header-derived column names) |
| STAGING | `APAC_LENDING_STAGING` | Cleaned names, typed numerics (`TRY_TO_NUMBER`), derived date parts, audit timestamps |
| DWH | `APAC_LENDING_DWH.DIM` / `.FACT` | Business-ready dimensions and AUD-enriched loan fact |
| MART | `APAC_LENDING_DWH.MART` | Monthly aggregated, BI-tool-ready tables |

Pipeline scripts live in [`snowflake_pipeline/`](snowflake_pipeline/). Credentials are read from environment variables (`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, optional `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`).

| Script | Purpose |
|---|---|
| `load_abs.py` | Load 3 ABS CSVs into RAW tables (PUT + COPY INTO) |
| `inspect_raw.py` / `profile_raw.py` | Column, frequency, null/distinct profiling of RAW |
| `build_staging.py` | Build ABS staging tables + QA report |
| `check_dupes.py` | Duplicate-row validation on staging |
| `build_dim.py` | Build ABS DWH dimension tables + label reports |
| `build_rba_fx.py` | Build RBA FX staging + AUD-enriched loan fact |
| `build_marts.py` | Build 3 business marts + validation |

## 3. Final Snowflake Objects

**APAC_LENDING_RAW**
- `ABS_DATA.RAW_ABS_BUSINESS_STRUCTURE`
- `ABS_DATA.RAW_ABS_BUSINESS_TURNOVER`
- `ABS_DATA.RAW_ABS_LABOUR_FORCE`
- `MARKET_DATA.RAW_RBA_EXCHANGE_RATES` *(pre-existing input, read-only)*

**APAC_LENDING_STAGING**
- `STG_ABS.STG_ABS_BUSINESS_STRUCTURE`
- `STG_ABS.STG_ABS_BUSINESS_TURNOVER`
- `STG_ABS.STG_ABS_LABOUR_FORCE`
- `STG_MARKET.STG_RBA_EXCHANGE_RATES`

**APAC_LENDING_DWH.DIM**
- `DIM_ABS_BUSINESS_STRUCTURE`
- `DIM_ABS_BUSINESS_TURNOVER`
- `DIM_ABS_LABOUR_FORCE`

**APAC_LENDING_DWH.FACT**
- `FCT_LENDING_CLUB_LOANS_AUD` *(new; base `FCT_LENDING_CLUB_LOANS` untouched)*

**APAC_LENDING_DWH.MART**
- `MART_PORTFOLIO_AUD_MONTHLY`
- `MART_APAC_MACRO_CONTEXT_MONTHLY`
- `MART_PORTFOLIO_WITH_MACRO_CONTEXT`

## 4. Key Row Counts (validated)

| Object | Rows |
|---|---|
| RAW_ABS_BUSINESS_STRUCTURE | 8,460 |
| RAW_ABS_BUSINESS_TURNOVER | 62,370 |
| RAW_ABS_LABOUR_FORCE | 431,520 |
| STG_ABS_BUSINESS_STRUCTURE | 8,460 |
| STG_ABS_BUSINESS_TURNOVER | 62,370 |
| STG_ABS_LABOUR_FORCE | 431,520 |
| DIM_ABS_BUSINESS_STRUCTURE | 5,735 |
| DIM_ABS_BUSINESS_TURNOVER | 61,599 |
| DIM_ABS_LABOUR_FORCE | 431,465 |
| STG_RBA_EXCHANGE_RATES | 1,004 (daily, 2014-01-02 → 2017-12-29) |
| FCT_LENDING_CLUB_LOANS_AUD | 1,347,681 (1,060,819 FX-matched / 286,862 missing rate) |
| MART_PORTFOLIO_AUD_MONTHLY | 139 (2007-06 → 2018-12) |
| MART_APAC_MACRO_CONTEXT_MONTHLY | 580 (1978-02 → 2026-05) |
| MART_PORTFOLIO_WITH_MACRO_CONTEXT | 139 (2007-06 → 2018-12) |

DIM counts are lower than staging because rows with null `obs_value` are excluded at the DWH layer (e.g. 2,725 nulls in business structure).

## 5. Business-Ready Marts

**`MART_PORTFOLIO_AUD_MONTHLY`** — one row per `issue_month`. Loan counts, USD and AUD totals for loan amount / estimated revenue / estimated risk, average applied USD→AUD rate, FX match-status counts, good/bad loan counts, average DTI.

**`MART_APAC_MACRO_CONTEXT_MONTHLY`** — one row per month, Australia-level, monthly ABS series only. Business turnover index and % change (seasonally adjusted, cross-industry average), unemployment rate, participation rate, employed persons, labour force persons (Persons / Seasonally Adjusted series).

**`MART_PORTFOLIO_WITH_MACRO_CONTEXT`** — executive mart: portfolio mart LEFT JOIN macro mart on `issue_month = period_month`. One row per issue month combining portfolio KPIs with macro indicators; ready for BI tools with no further joins.

## 6. Data Quality Checks Performed

- **Row counts** — verified at every layer (RAW → STAGING lossless: 8,460 / 62,370 / 431,520 preserved exactly).
- **Min/max dates** — validated per table (e.g. labour force 1978-02 → 2026-05; RBA rates 2014-01-02 → 2017-12-29; portfolio 2007-06 → 2018-12).
- **Null checks** — `obs_value` nulls quantified per staging table (2,725 / 771 / 55); zero nulls in DIM layer after filtering; mart-level null counts profiled for every key metric.
- **Numeric coercion** — 0 `TRY_TO_NUMBER` failures across all three ABS datasets (every non-null raw value converted cleanly; originals kept as `obs_value_raw`).
- **Duplicate checks** — 0 exact duplicate rows in all staging tables (verified via `DISTINCT * EXCLUDE (staged_at)`).
- **FX coverage checks** — match-status flagging shows 1,060,819 loans (78.7%) matched to actual RBA rates covering issue months 2014-01 → 2017-12; 286,862 outside coverage explicitly flagged `MISSING_EXCHANGE_RATE`.
- **Grain preservation** — fact row count unchanged after FX join (1,347,681 before and after); daily RBA rates were aggregated to monthly averages inline to prevent join fan-out; `issue_month` confirmed always first-of-month.

## 7. Known Limitations

1. **RBA FX coverage is 2014–2017 only.** Loans issued outside this window have NULL AUD amounts.
2. **No fallback FX rate used.** Unmatched rows are explicitly flagged, never estimated — by design, to preserve auditability.
3. **Turnover index is a cross-industry average proxy.** The ABS source has 55 industries but no "Total Industries" aggregate; the mart averages across industries, which is directional, not an official weighted national total.
4. **Business structure excluded from the monthly mart.** It is annual-only (2018–2020) and cannot safely be mapped to a monthly grain; it remains available in `DIM_ABS_BUSINESS_STRUCTURE`.
5. **No interest-rate column in the source fact.** `avg_interest_rate` could not be produced; `funded_amount` and `installment` were likewise absent, so no AUD variants exist for them.

## 8. CV-Ready Summary

*Analytics Engineer — International SME Fintech*

- Built an end-to-end Snowflake analytics warehouse (RAW → STAGING → DIM/FACT → MART) integrating a 1.35M-row lending portfolio with Australian Bureau of Statistics and Reserve Bank of Australia data, delivering dashboard-ready monthly marts for executive reporting.
- Engineered a currency-enrichment pipeline converting USD loan, revenue, and risk metrics to AUD using actual RBA exchange rates, with explicit FX match-status flagging, grain-preservation safeguards against join fan-out, and a strict no-fallback-rate policy for full auditability.
- Implemented layered data quality controls — lossless row-count reconciliation, zero-failure numeric coercion, duplicate and null profiling, and date-coverage validation — enabling reliable correlation analysis between lending performance and macroeconomic indicators (unemployment, participation, business turnover).
