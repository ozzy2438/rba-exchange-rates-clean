import os

import snowflake.connector

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "INGESTION_WH")

RAW_DB = "APAC_LENDING_RAW"
RAW_SCHEMA = "ABS_DATA"
STG_DB = "APAC_LENDING_STAGING"
STG_SCHEMA = "STG_ABS"

DDL_STATEMENTS = {
    "STG_ABS_BUSINESS_STRUCTURE": f"""
CREATE OR REPLACE TABLE {STG_DB}.{STG_SCHEMA}.STG_ABS_BUSINESS_STRUCTURE AS
SELECT
    "structure_id"                                                       AS dataflow_id,
    "structure_name"                                                     AS dataflow_name,
    "measure"                                                            AS measure_code,
    "measure_2"                                                          AS measure_label,
    "it_emp_size"                                                        AS employment_size_code,
    "employment_size"                                                    AS employment_size_label,
    "anzsic_2006"                                                        AS industry_code,
    "industry"                                                           AS industry_label,
    "innov_status"                                                       AS innovation_status_code,
    "innovation_status"                                                  AS innovation_status_label,
    "asgs_2016"                                                          AS region_code,
    "region"                                                             AS region_label,
    "frequency"                                                          AS freq_code,
    "frequency_2"                                                        AS freq_label,
    "time_period"                                                        AS "time_period",
    CASE WHEN "frequency" = 'A' THEN TRY_TO_NUMBER("time_period") END      AS period_year,
    CASE WHEN "frequency" = 'M' THEN TRY_TO_NUMBER(SPLIT_PART("time_period",'-',2)) END AS period_month,
    "obs_value"                                                          AS obs_value_raw,
    TRY_TO_NUMBER("obs_value", 38, 10)                                   AS "obs_value",
    "unit_measure"                                                       AS unit_measure_code,
    "unit_of_measure"                                                    AS unit_measure_label,
    "obs_status"                                                         AS obs_status_code,
    "observation_status"                                                 AS obs_status_label,
    "obs_comment"                                                        AS "obs_comment",
    CURRENT_TIMESTAMP()                                                AS staged_at
FROM {RAW_DB}.{RAW_SCHEMA}.RAW_ABS_BUSINESS_STRUCTURE
""",
    "STG_ABS_BUSINESS_TURNOVER": f"""
CREATE OR REPLACE TABLE {STG_DB}.{STG_SCHEMA}.STG_ABS_BUSINESS_TURNOVER AS
SELECT
    "structure_id"                                                       AS dataflow_id,
    "structure_name"                                                     AS dataflow_name,
    "measure"                                                            AS measure_code,
    "measure_2"                                                          AS measure_label,
    "price_adjustment"                                                   AS price_adjustment_code,
    "price_adjustment_2"                                                 AS price_adjustment_label,
    "tsest"                                                              AS adjustment_type_code,
    "adjustment_type"                                                    AS adjustment_type_label,
    "industry"                                                           AS industry_code,
    "industry_2"                                                         AS industry_label,
    "region"                                                             AS region_code,
    "region_2"                                                           AS region_label,
    "freq"                                                               AS freq_code,
    "frequency"                                                          AS freq_label,
    "time_period"                                                        AS "time_period",
    CASE WHEN "freq" = 'A' THEN TRY_TO_NUMBER("time_period")
         WHEN "freq" = 'M' THEN TRY_TO_NUMBER(SPLIT_PART("time_period",'-',1)) END AS period_year,
    CASE WHEN "freq" = 'M' THEN TRY_TO_NUMBER(SPLIT_PART("time_period",'-',2)) END AS period_month,
    "obs_value"                                                          AS obs_value_raw,
    TRY_TO_NUMBER("obs_value", 38, 10)                                   AS "obs_value",
    "unit_measure"                                                       AS unit_measure_code,
    "unit_of_measure"                                                    AS unit_measure_label,
    "unit_mult"                                                          AS unit_multiplier_code,
    "unit_of_multiplier"                                                 AS unit_multiplier_label,
    "obs_status"                                                         AS obs_status_code,
    "observation_status"                                                 AS obs_status_label,
    "obs_comment"                                                        AS "obs_comment",
    CURRENT_TIMESTAMP()                                                AS staged_at
FROM {RAW_DB}.{RAW_SCHEMA}.RAW_ABS_BUSINESS_TURNOVER
""",
    "STG_ABS_LABOUR_FORCE": f"""
CREATE OR REPLACE TABLE {STG_DB}.{STG_SCHEMA}.STG_ABS_LABOUR_FORCE AS
SELECT
    "structure_id"                                                       AS dataflow_id,
    "structure_name"                                                     AS dataflow_name,
    "measure"                                                            AS measure_code,
    "measure_2"                                                          AS measure_label,
    "sex"                                                                AS sex_code,
    "sex_2"                                                              AS sex_label,
    "age"                                                                AS age_code,
    "age_2"                                                              AS age_label,
    "tsest"                                                              AS adjustment_type_code,
    "adjustment_type"                                                    AS adjustment_type_label,
    "region"                                                             AS region_code,
    "region_2"                                                           AS region_label,
    "freq"                                                               AS freq_code,
    "frequency"                                                          AS freq_label,
    "time_period"                                                        AS "time_period",
    CASE WHEN "freq" = 'A' THEN TRY_TO_NUMBER("time_period")
         WHEN "freq" = 'M' THEN TRY_TO_NUMBER(SPLIT_PART("time_period",'-',1)) END AS period_year,
    CASE WHEN "freq" = 'M' THEN TRY_TO_NUMBER(SPLIT_PART("time_period",'-',2)) END AS period_month,
    "obs_value"                                                          AS obs_value_raw,
    TRY_TO_NUMBER("obs_value", 38, 10)                                   AS "obs_value",
    "unit_measure"                                                       AS unit_measure_code,
    "unit_of_measure"                                                    AS unit_measure_label,
    "unit_mult"                                                          AS unit_multiplier_code,
    "unit_of_multiplier"                                                 AS unit_multiplier_label,
    "obs_status"                                                         AS obs_status_code,
    "observation_status"                                                 AS obs_status_label,
    "obs_comment"                                                        AS "obs_comment",
    "decimals"                                                           AS decimals_code,
    "decimals_2"                                                         AS decimals_label,
    CURRENT_TIMESTAMP()                                                AS staged_at
FROM {RAW_DB}.{RAW_SCHEMA}.RAW_ABS_LABOUR_FORCE
""",
}


def main():
    conn = snowflake.connector.connect(
        account=ACCOUNT, user=USER, password=PASSWORD, role=ROLE, warehouse=WAREHOUSE
    )
    cs = conn.cursor()
    try:
        cs.execute(f"CREATE SCHEMA IF NOT EXISTS {STG_DB}.{STG_SCHEMA}")

        for table, ddl in DDL_STATEMENTS.items():
            cs.execute(ddl)

        print("REPORT")
        for table in DDL_STATEMENTS:
            full = f"{STG_DB}.{STG_SCHEMA}.{table}"

            cs.execute(f"SELECT COUNT(*) FROM {full}")
            row_count = cs.fetchone()[0]

            cs.execute(f'SELECT MIN("time_period"), MAX("time_period") FROM {full}')
            min_tp, max_tp = cs.fetchone()

            cs.execute(f'SELECT COUNT(*) FROM {full} WHERE "obs_value" IS NULL')
            obs_null = cs.fetchone()[0]

            cs.execute(
                f'SELECT COUNT(*) FROM {full} '
                f'WHERE OBS_VALUE_RAW IS NOT NULL AND "obs_value" IS NULL'
            )
            coercion_fail = cs.fetchone()[0]

            cols_sql = f"SELECT COUNT(*) - COUNT(DISTINCT * EXCLUDE (STAGED_AT)) FROM {full}"
            try:
                cs.execute(cols_sql)
                dup_count = cs.fetchone()[0]
            except Exception as e:
                dup_count = f"n/a ({e})"

            print(f"\n{table}")
            print(f"  row_count: {row_count}")
            print(f"  time_period min/max: {min_tp} / {max_tp}")
            print(f"  obs_value null count: {obs_null}")
            print(f"  obs_value coercion failures (raw present, numeric null): {coercion_fail}")
            print(f"  duplicate rows (excl staged_at): {dup_count}")
    finally:
        cs.close()
        conn.close()


if __name__ == "__main__":
    main()
