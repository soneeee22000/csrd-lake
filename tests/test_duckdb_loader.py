"""Tests for the DuckDB local-warehouse loader.

DuckDB runs in-process, so these are real round-trip integration tests against
an in-memory database (`:memory:`). No external services required.
"""

from __future__ import annotations

from datetime import UTC, datetime

import duckdb
import pytest

from csrd_lake.extraction.schemas import (
    ESRSMetric,
    ESRSTopic,
    ExtractionModel,
    Language,
    SourceCitation,
)
from csrd_lake.warehouse.duckdb_loader import (
    DUCKDB_DDL,
    INSERT_SQL_DUCKDB,
    TARGET_TABLE,
    bootstrap,
    load_metrics,
)


def _metric(**overrides: object) -> ESRSMetric:
    base: dict[str, object] = {
        "company_ticker": "SU.PA",
        "fiscal_year": 2024,
        "esrs_topic": ESRSTopic.E1_CLIMATE,
        "esrs_disclosure": "E1-6",
        "metric_name": "Total Scope 1 GHG emissions",
        "value_numeric": 106360.0,
        "unit": "tCO2e",
        "confidence_score": 0.95,
        "source_citation": SourceCitation(
            page=150,
            snippet="Scope 1 GHG emissions Gross Scope 1 GHG emissions 106,360 (tCOeq)",
        ),
        "language": Language.EN,
        "extraction_model": ExtractionModel.MISTRAL_LARGE,
        "extraction_timestamp": datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return ESRSMetric.model_validate(base)


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    """Fresh in-memory DuckDB with the RAW schema bootstrapped."""
    c = duckdb.connect(":memory:")
    c.execute(DUCKDB_DDL)
    yield c
    c.close()


class TestInsertShape:
    def test_insert_sql_uses_question_mark_placeholders(self) -> None:
        """DuckDB uses `?` placeholders, not Snowflake's `%s`."""
        assert "?" in INSERT_SQL_DUCKDB
        assert "%s" not in INSERT_SQL_DUCKDB
        assert TARGET_TABLE in INSERT_SQL_DUCKDB


class TestLoadMetrics:
    def test_empty_list_short_circuits(self, conn: duckdb.DuckDBPyConnection) -> None:
        assert load_metrics([], conn=conn) == 0
        assert conn.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}").fetchone()[0] == 0

    def test_single_metric_round_trips(self, conn: duckdb.DuckDBPyConnection) -> None:
        m = _metric()
        inserted = load_metrics([m], conn=conn)
        assert inserted == 1
        rows = conn.execute(
            f"SELECT company_ticker, esrs_disclosure, value_numeric, source_page FROM {TARGET_TABLE}"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == ("SU.PA", "E1-6", 106360, 150)

    def test_multiple_metrics_preserved(self, conn: duckdb.DuckDBPyConnection) -> None:
        ms = [
            _metric(esrs_disclosure="E1-6", metric_name="Scope 1", value_numeric=106360.0),
            _metric(esrs_disclosure="E1-6", metric_name="Scope 2 market", value_numeric=37348.0),
            _metric(
                esrs_disclosure="E1-2", metric_name="Net-zero target year", value_numeric=2050.0
            ),
        ]
        inserted = load_metrics(ms, conn=conn)
        assert inserted == 3
        count = conn.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}").fetchone()[0]
        assert count == 3

    def test_value_text_metric_preserved(self, conn: duckdb.DuckDBPyConnection) -> None:
        m = _metric(
            esrs_disclosure="E1-1",
            metric_name="Climate transition plan disclosed",
            value_numeric=None,
            value_text="Yes",
            unit="boolean",
        )
        load_metrics([m], conn=conn)
        row = conn.execute(f"SELECT value_numeric, value_text, unit FROM {TARGET_TABLE}").fetchone()
        assert row[0] is None
        assert row[1] == "Yes"
        assert row[2] == "boolean"


class TestBootstrap:
    def test_bootstrap_creates_file_and_schema(self, tmp_path) -> None:
        target = tmp_path / "warehouse" / "test.duckdb"
        conn = bootstrap(target)
        try:
            assert target.exists()
            schemas = {
                row[0]
                for row in conn.execute(
                    "SELECT schema_name FROM information_schema.schemata"
                ).fetchall()
            }
            assert "raw" in schemas
            assert "marts" in schemas
        finally:
            conn.close()
