"""Tests for the Snowflake bulk loader.

All tests use MagicMock connections — zero real Snowflake calls in CI.

Verifies:
- Load empty list short-circuits with zero DB calls
- Load N metrics calls executemany once with N rows
- Each row matches the column order in the INSERT SQL
- Datetime values pass through as Python datetime (Snowflake connector handles them)
- value_numeric / value_text exclusivity preserved per row
- Cursor is always closed (try/finally) even on error
- Exception in executemany propagates cleanly
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from csrd_lake.extraction.schemas import (
    ESRSMetric,
    ESRSTopic,
    ExtractionModel,
    Language,
    SourceCitation,
)
from csrd_lake.warehouse.loader import (
    INSERT_COLUMNS,
    INSERT_SQL,
    TARGET_TABLE,
    load_metrics,
    metric_to_row,
)

# ── Fixtures ──────────────────────────────────────────────────────────


def _metric(**overrides: object) -> ESRSMetric:
    base = {
        "company_ticker": "MC.PA",
        "fiscal_year": 2024,
        "esrs_topic": ESRSTopic.E1_CLIMATE,
        "esrs_disclosure": "E1-6",
        "metric_name": "Total Scope 1 GHG emissions",
        "value_numeric": 147500.0,
        "unit": "tCO2e",
        "confidence_score": 0.92,
        "source_citation": SourceCitation(
            page=42,
            snippet="Total Scope 1 GHG emissions for FY2024 amounted to 147,500 tCO2e.",
        ),
        "language": Language.EN,
        "extraction_model": ExtractionModel.CLAUDE_SONNET_4_6,
        "extraction_timestamp": datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return ESRSMetric.model_validate(base)


def _mock_conn(rowcount: int | None = None) -> MagicMock:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = rowcount if rowcount is not None else -1
    conn.cursor.return_value = cursor
    return conn


# ── load_metrics ──────────────────────────────────────────────────────


class TestLoadMetricsEmpty:
    def test_empty_list_returns_zero_no_db_call(self) -> None:
        conn = _mock_conn()
        assert load_metrics([], conn=conn) == 0
        conn.cursor.assert_not_called()


class TestLoadMetricsHappyPath:
    def test_single_metric_executemany_called_once(self) -> None:
        conn = _mock_conn(rowcount=1)
        result = load_metrics([_metric()], conn=conn)

        cursor = conn.cursor.return_value
        cursor.executemany.assert_called_once()
        sent_sql, sent_rows = cursor.executemany.call_args.args
        assert sent_sql == INSERT_SQL
        assert len(sent_rows) == 1
        assert result == 1

    def test_multiple_metrics_one_executemany_call(self) -> None:
        conn = _mock_conn(rowcount=3)
        metrics = [
            _metric(),
            _metric(esrs_disclosure="E1-5", metric_name="Energy", value_numeric=12345.0),
            _metric(
                esrs_disclosure="G1-1",
                metric_name="Business-conduct policy disclosed",
                value_numeric=None,
                value_text="Yes",
                unit="boolean",
            ),
        ]
        result = load_metrics(metrics, conn=conn)

        cursor = conn.cursor.return_value
        cursor.executemany.assert_called_once()
        _, sent_rows = cursor.executemany.call_args.args
        assert len(sent_rows) == 3
        assert result == 3

    def test_uses_target_table_in_sql(self) -> None:
        conn = _mock_conn(rowcount=1)
        load_metrics([_metric()], conn=conn)
        cursor = conn.cursor.return_value
        sent_sql, _ = cursor.executemany.call_args.args
        assert TARGET_TABLE in sent_sql
        # Sanity: SQL is parameterized — no f-string interpolation of values
        assert "%s" in sent_sql

    def test_returns_rowcount_when_available(self) -> None:
        conn = _mock_conn(rowcount=7)
        result = load_metrics([_metric() for _ in range(5)], conn=conn)
        # Snowflake reports rowcount; we trust it over the input length.
        assert result == 7

    def test_falls_back_to_input_length_when_rowcount_negative(self) -> None:
        conn = _mock_conn(rowcount=-1)  # -1 means "not available"
        result = load_metrics([_metric() for _ in range(4)], conn=conn)
        assert result == 4


# ── metric_to_row ─────────────────────────────────────────────────────


class TestMetricToRow:
    def test_row_columns_match_insert_columns_order(self) -> None:
        row = metric_to_row(_metric())
        assert len(row) == len(INSERT_COLUMNS)

    def test_row_field_values_correct(self) -> None:
        m = _metric()
        row = metric_to_row(m)
        # Column order is fixed in INSERT_COLUMNS — pluck by index for clarity
        cols = list(INSERT_COLUMNS)
        d = dict(zip(cols, row, strict=True))

        assert d["company_ticker"] == "MC.PA"
        assert d["fiscal_year"] == 2024
        assert d["esrs_topic"] == "E1"
        assert d["esrs_disclosure"] == "E1-6"
        assert d["value_numeric"] == 147500.0
        assert d["value_text"] is None
        assert d["unit"] == "tCO2e"
        assert d["confidence_score"] == 0.92
        assert d["source_page"] == 42
        assert "147,500 tCO2e" in d["source_snippet"]  # type: ignore[operator]
        assert d["language"] == "en"
        assert d["extraction_model"] == "claude-sonnet-4-6"
        assert d["extraction_timestamp"] == datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)

    def test_value_text_metric_serializes_with_null_numeric(self) -> None:
        m = _metric(
            esrs_disclosure="G1-1",
            metric_name="Business-conduct policy disclosed",
            value_numeric=None,
            value_text="Yes",
            unit="boolean",
        )
        row = metric_to_row(m)
        d = dict(zip(list(INSERT_COLUMNS), row, strict=True))
        assert d["value_numeric"] is None
        assert d["value_text"] == "Yes"
        assert d["unit"] == "boolean"


# ── Cleanup + error paths ─────────────────────────────────────────────


class TestCursorCleanup:
    def test_cursor_closed_on_success(self) -> None:
        conn = _mock_conn(rowcount=1)
        load_metrics([_metric()], conn=conn)
        conn.cursor.return_value.close.assert_called_once()

    def test_cursor_closed_on_error(self) -> None:
        conn = _mock_conn()
        cursor = conn.cursor.return_value
        cursor.executemany.side_effect = RuntimeError("snowflake exploded")

        with pytest.raises(RuntimeError, match="snowflake exploded"):
            load_metrics([_metric()], conn=conn)

        # Even though executemany blew up, cursor.close() must still have run.
        cursor.close.assert_called_once()
