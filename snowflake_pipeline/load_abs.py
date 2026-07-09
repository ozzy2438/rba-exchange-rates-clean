import csv
import os
import re
import sys

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")
DATABASE = "APAC_LENDING_RAW"
SCHEMA = "ABS_DATA"

FILES = [
    ("abs_business_structure.csv", "RAW_ABS_BUSINESS_STRUCTURE"),
    ("abs_business_turnover.csv", "RAW_ABS_BUSINESS_TURNOVER"),
    ("abs_labour_force.csv", "RAW_ABS_LABOUR_FORCE"),
]

SRC_DIR = "/Users/osmanorka/rba-exchange-rates-clean-1"


def clean_column_name(name, seen):
    name = name.strip()
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = name.strip("_").lower()
    if not name:
        name = "col"
    if re.match(r"^[0-9]", name):
        name = f"col_{name}"
    base = name
    i = 2
    while name in seen:
        name = f"{base}_{i}"
        i += 1
    seen.add(name)
    return name


def get_clean_header(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    seen = set()
    return [clean_column_name(h, seen) for h in header]


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT,
        user=USER,
        password=PASSWORD,
        role=ROLE,
        warehouse=WAREHOUSE,
    )
    cs = conn.cursor()
    try:
        cs.execute(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.{SCHEMA}")
        cs.execute(f"USE DATABASE {DATABASE}")
        cs.execute(f"USE SCHEMA {SCHEMA}")

        results = []
        for filename, table in FILES:
            path = os.path.join(SRC_DIR, filename)
            columns = get_clean_header(path)
            col_defs = ",\n    ".join(f'"{c}" VARCHAR(16777216)' for c in columns)

            cs.execute(f"CREATE OR REPLACE TABLE {SCHEMA}.{table} (\n    {col_defs}\n)")

            stage_name = f"{table}_STAGE"
            cs.execute(f"CREATE OR REPLACE TEMPORARY STAGE {SCHEMA}.{stage_name}")

            put_path = path.replace("\\", "\\\\").replace("'", "\\'")
            cs.execute(
                f"PUT 'file://{put_path}' @{SCHEMA}.{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            )

            copy_sql = f"""
            COPY INTO {SCHEMA}.{table}
            FROM @{SCHEMA}.{stage_name}
            FILE_FORMAT = (
                TYPE = CSV
                SKIP_HEADER = 1
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                EMPTY_FIELD_AS_NULL = TRUE
                ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
            )
            ON_ERROR = 'ABORT_STATEMENT'
            """
            cs.execute(copy_sql)

            cs.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
            count = cs.fetchone()[0]
            results.append((table, count))

        print("RESULTS")
        for table, count in results:
            print(f"{table}\t{count}")
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
