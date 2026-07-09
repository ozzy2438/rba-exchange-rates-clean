import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")
DATABASE = "APAC_LENDING_RAW"
SCHEMA = "ABS_DATA"

TABLES = [
    "RAW_ABS_BUSINESS_STRUCTURE",
    "RAW_ABS_BUSINESS_TURNOVER",
    "RAW_ABS_LABOUR_FORCE",
]


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"USE DATABASE {DATABASE}")
        cs.execute(f"USE SCHEMA {SCHEMA}")
        for table in TABLES:
            print(f"\n=== {table} ===")
            cs.execute(f"DESCRIBE TABLE {SCHEMA}.{table}")
            cols = [row[0] for row in cs.fetchall()]
            print("COLUMNS:", cols)

            cs.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
            print("ROW_COUNT:", cs.fetchone()[0])

            if "freq" in cols or "frequency" in cols:
                freq_col = "freq" if "freq" in cols else "frequency"
                cs.execute(
                    f'SELECT "{freq_col}", COUNT(*) FROM {SCHEMA}.{table} GROUP BY 1 ORDER BY 2 DESC'
                )
                print(f"DISTINCT {freq_col}:", cs.fetchall())

            cs.execute(
                f'SELECT MIN("time_period"), MAX("time_period") FROM {SCHEMA}.{table}'
            )
            print("TIME_PERIOD MIN/MAX:", cs.fetchone())

            cs.execute(
                f'SELECT "time_period" FROM {SCHEMA}.{table} '
                f'GROUP BY 1 ORDER BY RANDOM() LIMIT 8'
            )
            print("TIME_PERIOD SAMPLES:", [r[0] for r in cs.fetchall()])

            cs.execute(
                f'SELECT "obs_value", TRY_TO_NUMBER("obs_value") FROM {SCHEMA}.{table} '
                f'WHERE "obs_value" IS NOT NULL LIMIT 5'
            )
            print("OBS_VALUE SAMPLES (raw, try_to_number):", cs.fetchall())

            cs.execute(
                f'SELECT COUNT(*) FROM {SCHEMA}.{table} WHERE "obs_value" IS NULL'
            )
            print("OBS_VALUE NULL COUNT:", cs.fetchone()[0])

            cs.execute(
                f'SELECT COUNT(*) FROM {SCHEMA}.{table} '
                f'WHERE "obs_value" IS NOT NULL AND TRY_TO_NUMBER("obs_value") IS NULL'
            )
            print("OBS_VALUE NON-NUMERIC (not null but fails try_to_number):", cs.fetchone()[0])
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
