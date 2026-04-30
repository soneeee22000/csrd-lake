"""Snowflake bulk loader for ESRS extractions.

Writes a list of `ESRSMetric` into `RAW.DISCLOSURE_EXTRACTED` using the
Snowflake connector's parameterized `executemany`. Dimension tables are
populated separately by dbt seeds.

Design choices:
- Sync only — Airflow tasks are sync.
- Connection ownership is the caller's: we accept a live `conn` and never
  open or close it ourselves. This makes testing trivial and makes the
  Airflow `SnowflakeHook` integration straightforward.
- Cursor is always closed (try/finally), even on error.
- Empty list short-circuits to zero — no DB call.
- Idempotency at the load layer is not enforced; dbt staging de-duplicates
  on `(company_ticker, fiscal_year, esrs_disclosure, extraction_model)`.
"""

from __future__ import annotations

from typing import Any

import structlog

from csrd_lake.extraction.schemas import ESRSMetric

logger = structlog.get_logger(__name__)

# ── Target table + column ordering (must match DDL exactly) ───────────
TARGET_TABLE = "RAW.DISCLOSURE_EXTRACTED"

INSERT_COLUMNS: tuple[str, ...] = (
    "company_ticker",
    "fiscal_year",
    "esrs_topic",
    "esrs_disclosure",
    "metric_name",
    "value_numeric",
    "value_text",
    "unit",
    "confidence_score",
    "source_page",
    "source_snippet",
    "language",
    "extraction_model",
    "extraction_timestamp",
)

# Build the parameterized INSERT once at import time.
# Bandit S608 is a false positive here: TARGET_TABLE and INSERT_COLUMNS are
# module-level hardcoded constants with no path from user input. The %s
# placeholders ARE the parameterization for the actual values.
INSERT_SQL = (
    f"INSERT INTO {TARGET_TABLE} ({', '.join(INSERT_COLUMNS)}) "  # noqa: S608
    f"VALUES ({', '.join(['%s'] * len(INSERT_COLUMNS))})"
)


# ── Public entrypoint ─────────────────────────────────────────────────


def load_metrics(metrics: list[ESRSMetric], *, conn: Any) -> int:
    """Bulk-insert validated ESRS metrics into the raw landing table.

    Args:
        metrics: List of validated `ESRSMetric` instances. Empty list is a no-op.
        conn: A live Snowflake connection. The caller owns its lifecycle.

    Returns:
        Number of rows inserted. Prefers `cursor.rowcount` when Snowflake
        reports it; otherwise falls back to `len(metrics)`.
    """
    if not metrics:
        logger.debug("warehouse.load.skip", reason="empty_list")
        return 0

    rows = [metric_to_row(m) for m in metrics]
    cursor = conn.cursor()
    try:
        cursor.executemany(INSERT_SQL, rows)
        rowcount = (
            cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else len(rows)
        )
        logger.info("warehouse.load.success", rows=rowcount, target=TARGET_TABLE)
        return rowcount
    finally:
        cursor.close()


# ── Pure helper: ESRSMetric → tuple in INSERT_COLUMNS order ───────────


def metric_to_row(m: ESRSMetric) -> tuple[Any, ...]:
    """Map one `ESRSMetric` to the row tuple expected by `INSERT_SQL`.

    Order MUST match `INSERT_COLUMNS`. This mapping is the seam where the
    Pydantic schema crosses into Snowflake; tests pin both sides.
    """
    return (
        m.company_ticker,
        m.fiscal_year,
        m.esrs_topic.value,
        m.esrs_disclosure,
        m.metric_name,
        m.value_numeric,
        m.value_text,
        m.unit,
        m.confidence_score,
        m.source_citation.page,
        m.source_citation.snippet,
        m.language.value,
        m.extraction_model.value,
        m.extraction_timestamp,
    )
