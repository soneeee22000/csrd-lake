"""Smoke test — minimal cold-start sanity check.

Per the project CLAUDE.md, this MUST pass before any commit. It verifies:
1. The package imports cleanly
2. Pydantic schemas validate a known-good metric
3. Pydantic schemas reject a known-bad metric

Runs in <1s, requires no API keys, no Snowflake, no Airflow.
"""

import pytest
from pydantic import ValidationError

from csrd_lake import __version__
from csrd_lake.extraction.schemas import (
    ESRSMetric,
    ESRSTopic,
    ExtractionModel,
    Language,
    SourceCitation,
)


@pytest.mark.smoke
def test_package_imports() -> None:
    """Package imports and exposes a version."""
    assert __version__ == "0.1.0"


@pytest.mark.smoke
def test_valid_esrs_metric_validates() -> None:
    """A known-good ESRS metric passes Pydantic validation."""
    metric = ESRSMetric(
        company_ticker="MC.PA",
        fiscal_year=2024,
        esrs_topic=ESRSTopic.E1_CLIMATE,
        esrs_disclosure="E1-6",
        metric_name="Total Scope 1 GHG emissions",
        value_numeric=147500.0,
        unit="tCO2e",
        confidence_score=0.92,
        source_citation=SourceCitation(
            page=42,
            snippet="Total Scope 1 GHG emissions for FY2024 amounted to 147,500 tCO2e.",
        ),
        language=Language.EN,
        extraction_model=ExtractionModel.CLAUDE_SONNET_4_7,
    )
    assert metric.company_ticker == "MC.PA"
    assert metric.confidence_score == 0.92
    assert metric.source_citation.page == 42


@pytest.mark.smoke
def test_invalid_metric_rejects_both_values_populated() -> None:
    """Cannot populate both value_numeric and value_text."""
    with pytest.raises(ValidationError, match="Only one of value_numeric"):
        ESRSMetric(
            company_ticker="MC.PA",
            fiscal_year=2024,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            esrs_disclosure="E1-6",
            metric_name="Test",
            value_numeric=100.0,
            value_text="one hundred",  # both populated → error
            confidence_score=0.9,
            source_citation=SourceCitation(
                page=1,
                snippet="A snippet at least twenty characters long.",
            ),
            language=Language.EN,
            extraction_model=ExtractionModel.CLAUDE_SONNET_4_7,
        )


@pytest.mark.smoke
def test_invalid_metric_rejects_neither_value() -> None:
    """At least one of value_numeric or value_text must be populated."""
    with pytest.raises(ValidationError, match="Either value_numeric or value_text"):
        ESRSMetric(
            company_ticker="MC.PA",
            fiscal_year=2024,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            esrs_disclosure="E1-6",
            metric_name="Test",
            # neither value populated → error
            confidence_score=0.9,
            source_citation=SourceCitation(
                page=1,
                snippet="A snippet at least twenty characters long.",
            ),
            language=Language.EN,
            extraction_model=ExtractionModel.CLAUDE_SONNET_4_7,
        )


@pytest.mark.smoke
def test_invalid_metric_rejects_short_snippet() -> None:
    """Source-citation snippet must be ≥20 chars (audit trail integrity)."""
    with pytest.raises(ValidationError):
        SourceCitation(page=1, snippet="too short")


@pytest.mark.smoke
def test_invalid_metric_rejects_out_of_range_confidence() -> None:
    """Confidence score must be in [0, 1]."""
    with pytest.raises(ValidationError):
        ESRSMetric(
            company_ticker="MC.PA",
            fiscal_year=2024,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            esrs_disclosure="E1-6",
            metric_name="Test",
            value_numeric=100.0,
            confidence_score=1.5,  # out of range
            source_citation=SourceCitation(
                page=1,
                snippet="A snippet at least twenty characters long.",
            ),
            language=Language.EN,
            extraction_model=ExtractionModel.CLAUDE_SONNET_4_7,
        )
