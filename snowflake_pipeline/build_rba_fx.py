import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")

RAW_TABLE = "APAC_LENDING_RAW.MARKET_DATA.RAW_RBA_EXCHANGE_RATES"
FCT_TABLE = "APAC_LENDING_DWH.FACT.FCT_LENDING_CLUB_LOANS"

STG_DB = "APAC_LENDING_STAGING"
STG_SCHEMA = "STG_MARKET"
STG_TABLE = f"{STG_DB}.{STG_SCHEMA}.STG_RBA_EXCHANGE_RATES"

DWH_FACT_SCHEMA = "APAC_LENDING_DWH.FACT"
AUD_TABLE = f"{DWH_FACT_SCHEMA}.FCT_LENDING_CLUB_LOANS_AUD"

OTHER_CCY_COLS = [
    "AUD_TWI_INDEX", "AUD_TO_CNY", "AUD_TO_JPY", "AUD_TO_EUR", "AUD_TO_KRW",
    "AUD_TO_GBP", "AUD_TO_SGD", "AUD_TO_INR", "AUD_TO_THB", "AUD_TO_NZD",
    "AUD_TO_TWD", "AUD_TO_MYR", "AUD_TO_IDR", "AUD_TO_VND", "AUD_TO_AED",
    "AUD_TO_PGK", "AUD_TO_HKD", "AUD_TO_CAD", "AUD_TO_ZAR", "AUD_TO_CHF",
    "AUD_TO_PHP", "AUD_TO_SDR",
]

STG_DDL = f"""
CREATE OR REPLACE TABLE {STG_TABLE} AS
SELECT
    RATE_DATE,
    AUD_TO_USD,
    1.0 / AUD_TO_USD                    AS USD_TO_AUD,
    {", ".join(OTHER_CCY_COLS)},
    DATE_TRUNC('month', RATE_DATE)      AS RATE_MONTH,
    CURRENT_TIMESTAMP()                 AS STAGED_AT
FROM {RAW_TABLE}
"""

AUD_DDL = f"""
CREATE OR REPLACE TABLE {AUD_TABLE} AS
WITH monthly_rate AS (
    SELECT
        RATE_MONTH,
        AVG(AUD_TO_USD)         AS AUD_TO_USD,
        1.0 / AVG(AUD_TO_USD)   AS USD_TO_AUD
    FROM {STG_TABLE}
    GROUP BY RATE_MONTH
)
SELECT
    f.LOAN_KEY,
    f.LOAN_ID,
    f.ISSUE_MONTH,
    f.LOAN_PURPOSE_KEY,
    f.BORROWER_PROFILE_KEY,
    f.ANNUAL_INCOME_USD,
    f.DEBT_TO_INCOME_RATIO,
    f.LOAN_AMOUNT_USD,
    f.FICO_SCORE,
    f.IS_DEFAULTED,
    f.DEFAULT_FLAG,
    f.ESTIMATED_RISK_AMOUNT_USD,
    f.ESTIMATED_REVENUE_USD,
    f.SOURCE_SYSTEM,
    r.AUD_TO_USD,
    r.USD_TO_AUD,
    f.LOAN_AMOUNT_USD * r.USD_TO_AUD              AS LOAN_AMOUNT_AUD,
    f.ESTIMATED_REVENUE_USD * r.USD_TO_AUD         AS ESTIMATED_REVENUE_AUD,
    f.ESTIMATED_RISK_AMOUNT_USD * r.USD_TO_AUD     AS ESTIMATED_RISK_AMOUNT_AUD,
    CASE WHEN r.RATE_MONTH IS NOT NULL THEN 'ACTUAL_RBA_RATE_USED'
         ELSE 'MISSING_EXCHANGE_RATE' END          AS FX_MATCH_STATUS,
    CURRENT_TIMESTAMP()                            AS FX_ENRICHED_AT
FROM {FCT_TABLE} f
LEFT JOIN monthly_rate r
    ON f.ISSUE_MONTH = r.RATE_MONTH
"""


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"CREATE SCHEMA IF NOT EXISTS {STG_DB}.{STG_SCHEMA}")
        cs.execute(STG_DDL)
        cs.execute(AUD_DDL)

        print("=== STG_RBA_EXCHANGE_RATES ===")
        cs.execute(f"SELECT COUNT(*), MIN(RATE_DATE), MAX(RATE_DATE) FROM {STG_TABLE}")
        print(cs.fetchone())

        print("\n=== FCT_LENDING_CLUB_LOANS_AUD REPORT ===")
        cs.execute(f"SELECT COUNT(*) FROM {AUD_TABLE}")
        print("total_rows:", cs.fetchone()[0])

        cs.execute(f"SELECT FX_MATCH_STATUS, COUNT(*) FROM {AUD_TABLE} GROUP BY 1 ORDER BY 2 DESC")
        print("count by fx_match_status:", cs.fetchall())

        cs.execute(f"SELECT MIN(ISSUE_MONTH), MAX(ISSUE_MONTH) FROM {AUD_TABLE}")
        print("issue_month min/max:", cs.fetchone())

        cs.execute(
            f"SELECT MIN(f.ISSUE_MONTH), MAX(f.ISSUE_MONTH) FROM {AUD_TABLE} f "
            f"WHERE f.FX_MATCH_STATUS = 'ACTUAL_RBA_RATE_USED'"
        )
        print("matched issue_month min/max:", cs.fetchone())

        cs.execute(f"SELECT MIN(RATE_DATE), MAX(RATE_DATE) FROM {STG_TABLE}")
        print("underlying RBA rate_date min/max (source range used for matches):", cs.fetchone())

        cs.execute(f"SELECT SUM(LOAN_AMOUNT_USD) FROM {AUD_TABLE}")
        print("total loan_amount_usd:", cs.fetchone()[0])

        cs.execute(f"SELECT SUM(LOAN_AMOUNT_AUD) FROM {AUD_TABLE}")
        print("total loan_amount_aud (matched rows only):", cs.fetchone()[0])

        cs.execute(f"SELECT * FROM {AUD_TABLE} SAMPLE (20 ROWS)")
        cols = [d[0] for d in cs.description]
        print("\nSAMPLE COLUMNS:", cols)
        for row in cs.fetchall():
            print(row)
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
