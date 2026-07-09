import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")
DATABASE = "APAC_LENDING_RAW"
SCHEMA = "ABS_DATA"

TABLES = {
    "RAW_ABS_BUSINESS_STRUCTURE": ['structure', 'structure_id', 'structure_name', 'action', 'measure', 'measure_2', 'it_emp_size', 'employment_size', 'anzsic_2006', 'industry', 'innov_status', 'innovation_status', 'asgs_2016', 'region', 'frequency', 'frequency_2', 'time_period', 'time_period_2', 'obs_value', 'observation_value', 'unit_measure', 'unit_of_measure', 'obs_status', 'observation_status', 'obs_comment', 'observation_comment'],
    "RAW_ABS_BUSINESS_TURNOVER": ['structure', 'structure_id', 'structure_name', 'action', 'measure', 'measure_2', 'price_adjustment', 'price_adjustment_2', 'tsest', 'adjustment_type', 'industry', 'industry_2', 'region', 'region_2', 'freq', 'frequency', 'time_period', 'time_period_2', 'obs_value', 'observation_value', 'unit_measure', 'unit_of_measure', 'unit_mult', 'unit_of_multiplier', 'obs_status', 'observation_status', 'obs_comment', 'observation_comment'],
    "RAW_ABS_LABOUR_FORCE": ['structure', 'structure_id', 'structure_name', 'action', 'measure', 'measure_2', 'sex', 'sex_2', 'age', 'age_2', 'tsest', 'adjustment_type', 'region', 'region_2', 'freq', 'frequency', 'time_period', 'time_period_2', 'obs_value', 'observation_value', 'unit_measure', 'unit_of_measure', 'unit_mult', 'unit_of_multiplier', 'obs_status', 'observation_status', 'obs_comment', 'observation_comment', 'decimals', 'decimals_2'],
}


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"USE DATABASE {DATABASE}")
        cs.execute(f"USE SCHEMA {SCHEMA}")
        for table, cols in TABLES.items():
            print(f"\n=== {table} ===")
            parts = [
                f'COUNT(DISTINCT "{c}") AS "{c}__distinct", '
                f'SUM(IFF("{c}" IS NULL OR "{c}" = \'\', 1, 0)) AS "{c}__blank"'
                for c in cols
            ]
            sql = f"SELECT {', '.join(parts)} FROM {SCHEMA}.{table}"
            cs.execute(sql)
            row = cs.fetchone()
            desc = [d[0] for d in cs.description]
            vals = dict(zip(desc, row))
            for c in cols:
                print(f"{c:25s} distinct={vals[c+'__distinct']:<8} blank={vals[c+'__blank']}")
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
