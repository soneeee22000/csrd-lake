"""Local DuckDB loader for ESRS extractions — PRD fallback target.

Mirrors the Snowflake loader (`loader.py`) but writes to a local DuckDB file.
Used for local development and the cold-start demo (no cloud signup needed).
The DDL stays compatible with the Snowflake DDL so dbt models compile against
either target without branching.

Schema layout inside the DuckDB file:
    raw.disclosure_extracted   ← Python writer lands here
    marts.dim_company          ← dbt seed
    marts.dim_metric           ← dbt seed
    marts.dim_period           ← dbt seed
    marts.fact_disclosure      ← dbt model output
    marts.mart_disclosure_*    ← dbt model output
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from csrd_lake.warehouse.loader import INSERT_COLUMNS, metric_to_row

if TYPE_CHECKING:
    from csrd_lake.extraction.schemas import ESRSMetric

logger = structlog.get_logger(__name__)

DEFAULT_DUCKDB_PATH = Path("data/warehouse/csrd_lake.duckdb")
TARGET_TABLE = "raw.disclosure_extracted"

# DuckDB uses `?` placeholders. Column order matches `INSERT_COLUMNS` exactly.
INSERT_SQL_DUCKDB = (
    f"INSERT INTO {TARGET_TABLE} ({', '.join(INSERT_COLUMNS)}) "  # noqa: S608
    f"VALUES ({', '.join(['?'] * len(INSERT_COLUMNS))})"
)

# DDL kept inline (vs. ddl.sql) because DuckDB types differ slightly from Snowflake:
#   NUMBER(p,s)  -> DECIMAL(p,s)
#   IDENTITY     -> not used in raw table (append-only landing)
#   TIMESTAMP_TZ -> TIMESTAMPTZ
DUCKDB_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS raw.disclosure_extracted (
  company_ticker        VARCHAR(10)     NOT NULL,
  fiscal_year           SMALLINT        NOT NULL,
  esrs_topic            VARCHAR(2)      NOT NULL,
  esrs_disclosure       VARCHAR(20)     NOT NULL,
  metric_name           VARCHAR(200)    NOT NULL,
  value_numeric         DECIMAL(28, 6),
  value_text            VARCHAR(500),
  unit                  VARCHAR(50),
  confidence_score      DECIMAL(4, 3)   NOT NULL,
  source_page           INTEGER         NOT NULL,
  source_snippet        VARCHAR(500)    NOT NULL,
  language              VARCHAR(2)      NOT NULL,
  extraction_model      VARCHAR(50)     NOT NULL,
  extraction_timestamp  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def bootstrap(path: Path | None = None) -> Any:
    """Open (or create) a DuckDB warehouse file and ensure the RAW schema exists.

    Args:
        path: DuckDB file path. Defaults to `DEFAULT_DUCKDB_PATH`. The parent
            directory is created if missing.

    Returns:
        A live `duckdb.DuckDBPyConnection`. The caller owns its lifecycle.
    """
    import duckdb

    target = path or DEFAULT_DUCKDB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target))
    conn.execute(DUCKDB_DDL)
    logger.info("warehouse.duckdb.bootstrap", path=str(target))
    return conn


def load_metrics(metrics: list[ESRSMetric], *, conn: Any) -> int:
    """Bulk-insert validated ESRS metrics into the DuckDB raw landing table.

    Drop-in for `loader.load_metrics` but speaks DuckDB. Empty list short-circuits.
    """
    if not metrics:
        logger.debug("warehouse.duckdb.load.skip", reason="empty_list")
        return 0

    rows = [metric_to_row(m) for m in metrics]
    conn.executemany(INSERT_SQL_DUCKDB, rows)
    logger.info("warehouse.duckdb.load.success", rows=len(rows), target=TARGET_TABLE)
    return len(rows)
