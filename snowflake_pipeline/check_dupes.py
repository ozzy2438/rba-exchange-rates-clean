import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")

STG_DB = "APAC_LENDING_STAGING"
STG_SCHEMA = "STG_ABS"

TABLES = [
    "STG_ABS_BUSINESS_STRUCTURE",
    "STG_ABS_BUSINESS_TURNOVER",
    "STG_ABS_LABOUR_FORCE",
]


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        for table in TABLES:
            full = f"{STG_DB}.{STG_SCHEMA}.{table}"
            cs.execute(f"SELECT COUNT(*) FROM {full}")
            total = cs.fetchone()[0]
            cs.execute(
                f"SELECT COUNT(*) FROM (SELECT DISTINCT * EXCLUDE (STAGED_AT) FROM {full})"
            )
            distinct = cs.fetchone()[0]
            print(f"{table}: total={total} distinct_excl_staged_at={distinct} dup_rows={total - distinct}")
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
