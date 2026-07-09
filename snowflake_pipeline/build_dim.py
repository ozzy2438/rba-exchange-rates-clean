import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")

STG_DB = "APAC_LENDING_STAGING"
STG_SCHEMA = "STG_ABS"
DWH_DB = "APAC_LENDING_DWH"
DWH_SCHEMA = "DIM"

DDL_STATEMENTS = {
    "DIM_ABS_BUSINESS_STRUCTURE": f"""
CREATE OR REPLACE TABLE {DWH_DB}.{DWH_SCHEMA}.DIM_ABS_BUSINESS_STRUCTURE AS
SELECT
    MEASURE_CODE,
    MEASURE_LABEL,
    EMPLOYMENT_SIZE_CODE,
    EMPLOYMENT_SIZE_LABEL,
    INDUSTRY_CODE,
    INDUSTRY_LABEL,
    INNOVATION_STATUS_CODE,
    INNOVATION_STATUS_LABEL,
    REGION_CODE,
    REGION_LABEL,
    FREQ_CODE,
    FREQ_LABEL,
    "time_period"           AS TIME_PERIOD,
    PERIOD_YEAR,
    PERIOD_MONTH,
    "obs_value"              AS OBS_VALUE,
    UNIT_MEASURE_CODE,
    UNIT_MEASURE_LABEL,
    CURRENT_TIMESTAMP()      AS DWH_LOADED_AT
FROM {STG_DB}.{STG_SCHEMA}.STG_ABS_BUSINESS_STRUCTURE
WHERE "obs_value" IS NOT NULL
""",
    "DIM_ABS_BUSINESS_TURNOVER": f"""
CREATE OR REPLACE TABLE {DWH_DB}.{DWH_SCHEMA}.DIM_ABS_BUSINESS_TURNOVER AS
SELECT
    MEASURE_CODE,
    MEASURE_LABEL,
    PRICE_ADJUSTMENT_CODE,
    PRICE_ADJUSTMENT_LABEL,
    ADJUSTMENT_TYPE_CODE,
    ADJUSTMENT_TYPE_LABEL,
    INDUSTRY_CODE,
    INDUSTRY_LABEL,
    REGION_CODE,
    REGION_LABEL,
    FREQ_CODE,
    FREQ_LABEL,
    "time_period"           AS TIME_PERIOD,
    PERIOD_YEAR,
    PERIOD_MONTH,
    "obs_value"              AS OBS_VALUE,
    UNIT_MEASURE_CODE,
    UNIT_MEASURE_LABEL,
    UNIT_MULTIPLIER_CODE,
    UNIT_MULTIPLIER_LABEL,
    CURRENT_TIMESTAMP()      AS DWH_LOADED_AT
FROM {STG_DB}.{STG_SCHEMA}.STG_ABS_BUSINESS_TURNOVER
WHERE "obs_value" IS NOT NULL
""",
    "DIM_ABS_LABOUR_FORCE": f"""
CREATE OR REPLACE TABLE {DWH_DB}.{DWH_SCHEMA}.DIM_ABS_LABOUR_FORCE AS
SELECT
    MEASURE_CODE,
    MEASURE_LABEL,
    SEX_CODE,
    SEX_LABEL,
    AGE_CODE,
    AGE_LABEL,
    ADJUSTMENT_TYPE_CODE,
    ADJUSTMENT_TYPE_LABEL,
    REGION_CODE,
    REGION_LABEL,
    FREQ_CODE,
    FREQ_LABEL,
    "time_period"           AS TIME_PERIOD,
    PERIOD_YEAR,
    PERIOD_MONTH,
    "obs_value"              AS OBS_VALUE,
    UNIT_MEASURE_CODE,
    UNIT_MEASURE_LABEL,
    UNIT_MULTIPLIER_CODE,
    UNIT_MULTIPLIER_LABEL,
    DECIMALS_CODE,
    DECIMALS_LABEL,
    CURRENT_TIMESTAMP()      AS DWH_LOADED_AT
FROM {STG_DB}.{STG_SCHEMA}.STG_ABS_LABOUR_FORCE
WHERE "obs_value" IS NOT NULL
""",
}

LABEL_COLS = {
    "DIM_ABS_BUSINESS_STRUCTURE": {
        "measure": "MEASURE_LABEL",
        "region": "REGION_LABEL",
        "industry": "INDUSTRY_LABEL",
    },
    "DIM_ABS_BUSINESS_TURNOVER": {
        "measure": "MEASURE_LABEL",
        "region": "REGION_LABEL",
        "industry": "INDUSTRY_LABEL",
    },
    "DIM_ABS_LABOUR_FORCE": {
        "measure": "MEASURE_LABEL",
        "region": "REGION_LABEL",
        "industry": None,
    },
}


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"CREATE SCHEMA IF NOT EXISTS {DWH_DB}.{DWH_SCHEMA}")

        for table, ddl in DDL_STATEMENTS.items():
            cs.execute(ddl)

        print("REPORT")
        for table in DDL_STATEMENTS:
            full = f"{DWH_DB}.{DWH_SCHEMA}.{table}"

            cs.execute(f"SELECT COUNT(*) FROM {full}")
            row_count = cs.fetchone()[0]

            cs.execute(f"SELECT MIN(TIME_PERIOD), MAX(TIME_PERIOD) FROM {full}")
            min_tp, max_tp = cs.fetchone()

            cs.execute(f"SELECT COUNT(*) FROM {full} WHERE OBS_VALUE IS NULL")
            obs_null = cs.fetchone()[0]

            print(f"\n{table}")
            print(f"  row_count: {row_count}")
            print(f"  time_period min/max: {min_tp} / {max_tp}")
            print(f"  obs_value null count: {obs_null}")

            for dim, col in LABEL_COLS[table].items():
                if col is None:
                    print(f"  top10 {dim}: n/a (no {dim} column in this table)")
                    continue
                cs.execute(
                    f"SELECT {col}, COUNT(*) c FROM {full} "
                    f"GROUP BY {col} ORDER BY c DESC LIMIT 10"
                )
                rows = cs.fetchall()
                print(f"  top10 {dim} labels:")
                for label, cnt in rows:
                    print(f"    {label}: {cnt}")
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
