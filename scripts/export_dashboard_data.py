"""Export warehouse rows into a JSON snapshot the Next.js dashboard imports.

The Vercel build cannot query the warehouse at runtime — it has no access to
the local .duckdb file or to Snowflake. Instead we run this script after
`dbt run` to dump the marts to `dashboard/lib/data/disclosures.json`, which
is committed to the repo and imported statically by `dashboard/lib/data.ts`.
Re-runs of the batch should re-export.

Two warehouse sources are supported:
  --source duckdb     (default) reads from the local .duckdb file
  --source snowflake  reads from the Snowflake account configured in .env

Both produce identical JSON output — the dashboard cannot tell which warehouse
sourced the snapshot. The `extractedAt` field is stamped at export time and the
`warehouse` field records which engine answered the query.

Usage:
    python scripts/export_dashboard_data.py
    python scripts/export_dashboard_data.py --source snowflake
    python scripts/export_dashboard_data.py --duckdb path/to/csrd.duckdb --out dashboard/lib/data/disclosures.json

The JSON shape mirrors the TypeScript types in `dashboard/lib/data.ts`:

    {
      "fiscalYear": 2024,
      "extractedAt": "2026-05-02T15:58:00+00:00",
      "companies": [{ticker, name, sector, country, language}, ...],
      "disclosuresByTicker": {
        "MC.PA": [{id, esrsTopic, esrsDisclosure, metricName,
                   valueNumeric, valueText, unit, confidenceScore,
                   sourcePage, sourceSnippet, language, extractionModel}, ...],
        ...
      }
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DUCKDB = Path("data/warehouse/csrd_lake.duckdb")
DEFAULT_OUT = Path("dashboard/lib/data/disclosures.json")
DEFAULT_FISCAL_YEAR = 2024

# We pull the deduplicated view of raw.disclosure_extracted so the dashboard
# always shows the latest extraction per natural key (matches stg_disclosure).
# {placeholder} is filled with `?` for DuckDB or `%s` for Snowflake.
DISCLOSURES_SQL_TEMPLATE = """
WITH ranked AS (
    SELECT
        company_ticker,
        fiscal_year,
        esrs_topic,
        esrs_disclosure,
        metric_name,
        value_numeric,
        value_text,
        unit,
        confidence_score,
        source_page,
        source_snippet,
        language,
        extraction_model,
        extraction_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY company_ticker, fiscal_year, esrs_disclosure, metric_name, extraction_model
            ORDER BY extraction_timestamp DESC
        ) AS rn
    FROM raw.disclosure_extracted
    WHERE fiscal_year = {placeholder}
)
SELECT
    company_ticker,
    esrs_topic,
    esrs_disclosure,
    metric_name,
    value_numeric,
    value_text,
    unit,
    confidence_score,
    source_page,
    source_snippet,
    language,
    extraction_model
FROM ranked
WHERE rn = 1
-- Deterministic order: tie-break on metric_name + extraction_model so DuckDB
-- and Snowflake exports are byte-identical (multiple metrics share one
-- esrs_disclosure code in real CSRD reports).
ORDER BY company_ticker, esrs_topic, esrs_disclosure, metric_name, extraction_model
"""

COMPANIES_SQL = """
SELECT ticker, name, sector, country, language
FROM dim_company
ORDER BY ticker
"""


def _row_to_metric(row: tuple, idx: int) -> dict:
    (
        ticker,
        topic,
        disclosure,
        metric_name,
        value_numeric,
        value_text,
        unit,
        confidence,
        page,
        snippet,
        language,
        extraction_model,
    ) = row
    return {
        "id": f"{ticker}-{idx}",
        "esrsTopic": topic,
        "esrsDisclosure": disclosure,
        "metricName": metric_name,
        "valueNumeric": float(value_numeric) if value_numeric is not None else None,
        "valueText": value_text,
        "unit": unit,
        "confidenceScore": float(confidence),
        "sourcePage": int(page),
        "sourceSnippet": snippet,
        "language": language,
        "extractionModel": extraction_model,
    }


def _resolve_dim_company_relation_duckdb(conn) -> str:
    """dbt-duckdb materialises seeds at `marts_MARTS.dim_company` by default
    (profile schema `marts` + seed schema override `MARTS`). Detect the actual
    table name so the export works against either layout.
    """
    rows = conn.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name = 'dim_company'
        """
    ).fetchall()
    if not rows:
        raise RuntimeError("dim_company not found - run `dbt seed && dbt run` first.")
    schema, table = rows[0]
    return f"{schema}.{table}"


def _resolve_dim_company_relation_snowflake(conn) -> str:
    """Snowflake stores unquoted identifiers in uppercase, so the lookup
    matches DIM_COMPANY across whatever schema dbt wrote it to (e.g.
    RAW_MARTS when DBT_TARGET=dev with SNOWFLAKE_SCHEMA=RAW).

    Picks the candidate with the highest row_count, so stale empty leftovers
    from earlier dbt runs with a different target schema can't shadow the
    current build.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT table_schema, table_name, row_count
            FROM information_schema.tables
            WHERE UPPER(table_name) = 'DIM_COMPANY'
            ORDER BY row_count DESC NULLS LAST, table_schema
            """
        )
        rows = cur.fetchall()
    finally:
        cur.close()
    if not rows:
        raise RuntimeError(
            "DIM_COMPANY not found in Snowflake - "
            "run `python scripts/dbt_run.py seed run --target dev` first."
        )
    schema, table, _row_count = rows[0]
    return f"{schema}.{table}"


def _query_duckdb(duckdb_path: Path, fiscal_year: int) -> tuple[list[tuple], list[tuple]]:
    """Pull (companies, disclosure_rows) from a local .duckdb file."""
    import duckdb

    conn = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        dim_company_relation = _resolve_dim_company_relation_duckdb(conn)
        company_rows = conn.execute(
            COMPANIES_SQL.replace("dim_company", dim_company_relation)
        ).fetchall()
        sql = DISCLOSURES_SQL_TEMPLATE.format(placeholder="?")
        disclosure_rows = conn.execute(sql, [fiscal_year]).fetchall()
    finally:
        conn.close()
    return company_rows, disclosure_rows


def _query_snowflake(fiscal_year: int) -> tuple[list[tuple], list[tuple]]:
    """Pull (companies, disclosure_rows) from the Snowflake account configured
    in .env. Reuses bootstrap_snowflake._connect so credentials and key-pair
    handling stay in one place.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.bootstrap_snowflake import _connect

    conn = _connect()
    try:
        dim_company_relation = _resolve_dim_company_relation_snowflake(conn)
        cur = conn.cursor()
        try:
            cur.execute(COMPANIES_SQL.replace("dim_company", dim_company_relation))
            company_rows = cur.fetchall()
            sql = DISCLOSURES_SQL_TEMPLATE.format(placeholder="%s")
            cur.execute(sql, (fiscal_year,))
            disclosure_rows = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()
    return company_rows, disclosure_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        choices=("duckdb", "snowflake"),
        default="duckdb",
        help="Which warehouse to read from (default: duckdb).",
    )
    parser.add_argument("--duckdb", type=Path, default=DEFAULT_DUCKDB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fiscal-year", type=int, default=DEFAULT_FISCAL_YEAR)
    args = parser.parse_args()

    if args.source == "duckdb":
        if not args.duckdb.exists():
            print(f"ERROR: DuckDB file not found: {args.duckdb}", file=sys.stderr)
            print("       Run `python -m csrd_lake.extraction.batch` first.", file=sys.stderr)
            return 1
        company_rows, disclosure_rows = _query_duckdb(args.duckdb, args.fiscal_year)
    else:
        from dotenv import load_dotenv

        load_dotenv()
        company_rows, disclosure_rows = _query_snowflake(args.fiscal_year)

    companies = [
        {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "country": country,
            "language": language,
        }
        for ticker, name, sector, country, language in company_rows
    ]

    by_ticker: dict[str, list[dict]] = {}
    for row in disclosure_rows:
        by_ticker.setdefault(row[0], [])
    for row in disclosure_rows:
        ticker = row[0]
        by_ticker[ticker].append(_row_to_metric(row, idx=len(by_ticker[ticker])))

    payload = {
        "fiscalYear": args.fiscal_year,
        "extractedAt": datetime.now(UTC).isoformat(),
        "warehouse": args.source,
        "companies": companies,
        "disclosuresByTicker": by_ticker,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    total_metrics = sum(len(v) for v in by_ticker.values())
    companies_with_data = sum(1 for v in by_ticker.values() if v)
    print(f"OK exported {len(companies)} companies, {total_metrics} metrics from {args.source}")
    print(f"   wrote -> {args.out}")
    print(f"   {companies_with_data} of {len(companies)} companies have at least one extraction")
    return 0


if __name__ == "__main__":
    sys.exit(main())
