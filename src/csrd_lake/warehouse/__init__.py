"""Snowflake warehouse layer.

- ddl.sql                  — star schema DDL (dim_company, dim_metric,
                             dim_period, fact_disclosure, raw landing table)
- loader.py                — bulk-load list[ESRSMetric] into the raw table
                             using parameterized executemany

The dimension tables are populated by dbt seeds from the company manifest +
ESRS catalog. The loader's only job is to land extractions into the raw
table; dbt staging + marts handle de-duplication, type cleanup, and the
confidence-score routing split (`mart_disclosure_published` /
`mart_disclosure_review_queue`).
"""
