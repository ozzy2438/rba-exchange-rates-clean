import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")

FCT_AUD = "APAC_LENDING_DWH.FACT.FCT_LENDING_CLUB_LOANS_AUD"
DIM_TURNOVER = "APAC_LENDING_DWH.DIM.DIM_ABS_BUSINESS_TURNOVER"
DIM_LABOUR = "APAC_LENDING_DWH.DIM.DIM_ABS_LABOUR_FORCE"

MART_SCHEMA = "APAC_LENDING_DWH.MART"
MART_PORTFOLIO = f"{MART_SCHEMA}.MART_PORTFOLIO_AUD_MONTHLY"
MART_MACRO = f"{MART_SCHEMA}.MART_APAC_MACRO_CONTEXT_MONTHLY"
MART_JOINED = f"{MART_SCHEMA}.MART_PORTFOLIO_WITH_MACRO_CONTEXT"

PORTFOLIO_DDL = f"""
CREATE OR REPLACE TABLE {MART_PORTFOLIO} AS
SELECT
    ISSUE_MONTH                                                            AS ISSUE_MONTH,
    COUNT(*)                                                               AS LOAN_COUNT,
    SUM(LOAN_AMOUNT_USD)                                                   AS TOTAL_LOAN_AMOUNT_USD,
    SUM(LOAN_AMOUNT_AUD)                                                   AS TOTAL_LOAN_AMOUNT_AUD,
    SUM(ESTIMATED_REVENUE_USD)                                             AS TOTAL_ESTIMATED_REVENUE_USD,
    SUM(ESTIMATED_REVENUE_AUD)                                             AS TOTAL_ESTIMATED_REVENUE_AUD,
    SUM(ESTIMATED_RISK_AMOUNT_USD)                                         AS TOTAL_ESTIMATED_RISK_AMOUNT_USD,
    SUM(ESTIMATED_RISK_AMOUNT_AUD)                                         AS TOTAL_ESTIMATED_RISK_AMOUNT_AUD,
    AVG(USD_TO_AUD)                                                        AS AVG_APPLIED_USD_TO_AUD,
    SUM(CASE WHEN FX_MATCH_STATUS = 'ACTUAL_RBA_RATE_USED' THEN 1 ELSE 0 END) AS ACTUAL_RBA_RATE_USED_COUNT,
    SUM(CASE WHEN FX_MATCH_STATUS = 'MISSING_EXCHANGE_RATE' THEN 1 ELSE 0 END) AS MISSING_EXCHANGE_RATE_COUNT,
    SUM(CASE WHEN DEFAULT_FLAG = 1 THEN 1 ELSE 0 END)                      AS BAD_LOAN_COUNT,
    SUM(CASE WHEN DEFAULT_FLAG = 0 THEN 1 ELSE 0 END)                      AS GOOD_LOAN_COUNT,
    AVG(DEBT_TO_INCOME_RATIO)                                              AS AVG_DTI,
    CURRENT_TIMESTAMP()                                                    AS MART_LOADED_AT
FROM {FCT_AUD}
GROUP BY ISSUE_MONTH
"""

MACRO_DDL = f"""
CREATE OR REPLACE TABLE {MART_MACRO} AS
WITH turnover AS (
    SELECT
        DATE_FROM_PARTS(PERIOD_YEAR, PERIOD_MONTH, 1)                                          AS PERIOD_MONTH,
        AVG(CASE WHEN MEASURE_LABEL = 'Business Turnover Index' THEN OBS_VALUE END)             AS BUSINESS_TURNOVER_INDEX,
        AVG(CASE WHEN MEASURE_LABEL = 'Business Turnover Percentage Change' THEN OBS_VALUE END) AS BUSINESS_TURNOVER_PCT_CHANGE
    FROM {DIM_TURNOVER}
    WHERE REGION_LABEL = 'Australia'
      AND ADJUSTMENT_TYPE_LABEL = 'Seasonally Adjusted'
      AND FREQ_CODE = 'M'
    GROUP BY 1
),
labour AS (
    SELECT
        DATE_FROM_PARTS(PERIOD_YEAR, PERIOD_MONTH, 1)                          AS PERIOD_MONTH,
        MAX(CASE WHEN MEASURE_LABEL = 'Unemployment rate' THEN OBS_VALUE END)  AS UNEMPLOYMENT_RATE,
        MAX(CASE WHEN MEASURE_LABEL = 'Participation rate' THEN OBS_VALUE END) AS PARTICIPATION_RATE,
        MAX(CASE WHEN MEASURE_LABEL = 'Employed persons' THEN OBS_VALUE END)   AS EMPLOYED_PERSONS,
        MAX(CASE WHEN MEASURE_LABEL = 'Labour Force' THEN OBS_VALUE END)       AS LABOUR_FORCE_PERSONS
    FROM {DIM_LABOUR}
    WHERE REGION_LABEL = 'Australia'
      AND SEX_LABEL = 'Persons'
      AND ADJUSTMENT_TYPE_LABEL = 'Seasonally Adjusted'
      AND FREQ_CODE = 'M'
    GROUP BY 1
)
SELECT
    COALESCE(t.PERIOD_MONTH, l.PERIOD_MONTH) AS PERIOD_MONTH,
    t.BUSINESS_TURNOVER_INDEX,
    t.BUSINESS_TURNOVER_PCT_CHANGE,
    l.UNEMPLOYMENT_RATE,
    l.PARTICIPATION_RATE,
    l.EMPLOYED_PERSONS,
    l.LABOUR_FORCE_PERSONS,
    CURRENT_TIMESTAMP() AS MART_LOADED_AT
FROM turnover t
FULL OUTER JOIN labour l ON t.PERIOD_MONTH = l.PERIOD_MONTH
"""

JOINED_DDL = f"""
CREATE OR REPLACE TABLE {MART_JOINED} AS
SELECT
    p.ISSUE_MONTH,
    p.LOAN_COUNT,
    p.TOTAL_LOAN_AMOUNT_USD,
    p.TOTAL_LOAN_AMOUNT_AUD,
    p.TOTAL_ESTIMATED_REVENUE_USD,
    p.TOTAL_ESTIMATED_REVENUE_AUD,
    p.TOTAL_ESTIMATED_RISK_AMOUNT_USD,
    p.TOTAL_ESTIMATED_RISK_AMOUNT_AUD,
    p.AVG_APPLIED_USD_TO_AUD,
    p.ACTUAL_RBA_RATE_USED_COUNT,
    p.MISSING_EXCHANGE_RATE_COUNT,
    p.BAD_LOAN_COUNT,
    p.GOOD_LOAN_COUNT,
    p.AVG_DTI,
    m.BUSINESS_TURNOVER_INDEX,
    m.BUSINESS_TURNOVER_PCT_CHANGE,
    m.UNEMPLOYMENT_RATE,
    m.PARTICIPATION_RATE,
    m.EMPLOYED_PERSONS,
    m.LABOUR_FORCE_PERSONS,
    CURRENT_TIMESTAMP() AS MART_LOADED_AT
FROM {MART_PORTFOLIO} p
LEFT JOIN {MART_MACRO} m
    ON p.ISSUE_MONTH = m.PERIOD_MONTH
"""


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"CREATE SCHEMA IF NOT EXISTS {MART_SCHEMA}")
        cs.execute(PORTFOLIO_DDL)
        cs.execute(MACRO_DDL)
        cs.execute(JOINED_DDL)

        for name, table, month_col in [
            ("MART_PORTFOLIO_AUD_MONTHLY", MART_PORTFOLIO, "ISSUE_MONTH"),
            ("MART_APAC_MACRO_CONTEXT_MONTHLY", MART_MACRO, "PERIOD_MONTH"),
            ("MART_PORTFOLIO_WITH_MACRO_CONTEXT", MART_JOINED, "ISSUE_MONTH"),
        ]:
            print(f"\n=== {name} ===")
            cs.execute(f"SELECT COUNT(*), MIN({month_col}), MAX({month_col}) FROM {table}")
            print("row_count, min_month, max_month:", cs.fetchone())

        print("\n--- MART_PORTFOLIO_AUD_MONTHLY null checks ---")
        cs.execute(f"""
            SELECT
                SUM(IFF(TOTAL_LOAN_AMOUNT_AUD IS NULL,1,0)) AS null_loan_amount_aud,
                SUM(IFF(AVG_APPLIED_USD_TO_AUD IS NULL,1,0)) AS null_avg_fx,
                SUM(IFF(BAD_LOAN_COUNT IS NULL,1,0)) AS null_bad_loan_count,
                SUM(IFF(AVG_DTI IS NULL,1,0)) AS null_avg_dti
            FROM {MART_PORTFOLIO}
        """)
        print(cs.fetchone())

        print("\n--- MART_APAC_MACRO_CONTEXT_MONTHLY null checks ---")
        cs.execute(f"""
            SELECT
                SUM(IFF(BUSINESS_TURNOVER_INDEX IS NULL,1,0)) AS null_turnover_idx,
                SUM(IFF(BUSINESS_TURNOVER_PCT_CHANGE IS NULL,1,0)) AS null_turnover_pct,
                SUM(IFF(UNEMPLOYMENT_RATE IS NULL,1,0)) AS null_unemployment,
                SUM(IFF(PARTICIPATION_RATE IS NULL,1,0)) AS null_participation,
                SUM(IFF(EMPLOYED_PERSONS IS NULL,1,0)) AS null_employed,
                SUM(IFF(LABOUR_FORCE_PERSONS IS NULL,1,0)) AS null_labour_force
            FROM {MART_MACRO}
        """)
        print(cs.fetchone())

        print("\n--- MART_PORTFOLIO_WITH_MACRO_CONTEXT null checks ---")
        cs.execute(f"""
            SELECT
                SUM(IFF(UNEMPLOYMENT_RATE IS NULL,1,0)) AS null_unemployment,
                SUM(IFF(BUSINESS_TURNOVER_INDEX IS NULL,1,0)) AS null_turnover_idx,
                SUM(IFF(TOTAL_LOAN_AMOUNT_AUD IS NULL,1,0)) AS null_loan_amount_aud
            FROM {MART_JOINED}
        """)
        print(cs.fetchone())

        print("\n--- SAMPLE 20 rows from MART_PORTFOLIO_WITH_MACRO_CONTEXT ---")
        cs.execute(f"SELECT * FROM {MART_JOINED} ORDER BY ISSUE_MONTH LIMIT 20")
        cols = [d[0] for d in cs.description]
        print(cols)
        for row in cs.fetchall():
            print(row)
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
