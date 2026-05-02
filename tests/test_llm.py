"""Tests for the LLM extraction layer.

All tests use MagicMock SDK clients — zero real API calls in CI.

Verifies:
- Successful Claude extraction returns valid ESRSMetric list with correct fields
- Claude raises → falls back to Mistral
- Claude returns malformed/invalid output → falls back to Mistral
- Both raise → ExtractionError propagates
- Empty extraction (no metrics found) returns empty list
- Source citation page is offset correctly relative to chunk-start
- Confidence score is computed (not zero on a clean extraction)
- Language tag is propagated from manifest
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from csrd_lake.extraction.llm import ExtractionError, extract_esrs_metrics
from csrd_lake.extraction.schemas import ESRSMetric, ESRSTopic, ExtractionModel, Language
from csrd_lake.ingestion.manifest import CompanyEntry

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def lvmh() -> CompanyEntry:
    return CompanyEntry(
        ticker="MC.PA",
        name="LVMH",
        sector="Luxury",
        country="FR",
        ir_page_url="https://www.lvmh.com/investors/",
        language="fr",
    )


@pytest.fixture
def good_metric_payload() -> dict[str, object]:
    """A well-formed metric payload that parses cleanly into ESRSMetric."""
    return {
        "esrs_disclosure": "E1-6",
        "metric_name": "Total Scope 1 GHG emissions",
        "value_numeric": 147500.0,
        "value_text": None,
        "unit": "tCO2e",
        "model_confidence": 0.92,
        "source_page": 42,
        "source_snippet": "Total Scope 1 GHG emissions for FY2024 amounted to 147,500 tCO2e.",
    }


def _claude_tool_response(metrics_payload: list[dict[str, object]]) -> MagicMock:
    """Build a MagicMock that quacks like an Anthropic Messages.create response."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = {"metrics": metrics_payload}
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


def _mistral_response(metrics_payload: list[dict[str, object]]) -> MagicMock:
    """Build a MagicMock that quacks like a Mistral chat.complete response."""
    import json

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({"metrics": metrics_payload})
    return response


# ── Happy path ───────────────────────────────────────────────────────


class TestSuccessfulExtraction:
    def test_claude_extraction_returns_valid_metrics(
        self, lvmh: CompanyEntry, good_metric_payload: dict[str, object]
    ) -> None:
        anthropic = MagicMock()
        anthropic.messages.create.return_value = _claude_tool_response([good_metric_payload])
        mistral = MagicMock()  # never called

        metrics = extract_esrs_metrics(
            pdf_text="Total Scope 1 GHG emissions for FY2024 amounted to 147,500 tCO2e.",
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=mistral,
        )

        assert len(metrics) == 1
        m = metrics[0]
        assert isinstance(m, ESRSMetric)
        assert m.company_ticker == "MC.PA"
        assert m.fiscal_year == 2024
        assert m.esrs_topic == ESRSTopic.E1_CLIMATE
        assert m.value_numeric == 147500.0
        assert m.unit == "tCO2e"
        assert m.source_citation.page == 42
        assert m.language == Language.FR
        assert m.extraction_model == ExtractionModel.CLAUDE_SONNET_4_6
        # Mistral fallback was not used
        mistral.chat.complete.assert_not_called()

    def test_confidence_score_is_computed_nonzero(
        self, lvmh: CompanyEntry, good_metric_payload: dict[str, object]
    ) -> None:
        """Clean extraction with snippet match → confidence > 0."""
        anthropic = MagicMock()
        anthropic.messages.create.return_value = _claude_tool_response([good_metric_payload])

        metrics = extract_esrs_metrics(
            pdf_text=good_metric_payload["source_snippet"],  # type: ignore[arg-type]
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=MagicMock(),
        )
        assert metrics[0].confidence_score > 0.5

    def test_empty_extraction_returns_empty_list(self, lvmh: CompanyEntry) -> None:
        """If the LLM finds no metrics in the chunk, return []."""
        anthropic = MagicMock()
        anthropic.messages.create.return_value = _claude_tool_response([])

        metrics = extract_esrs_metrics(
            pdf_text="boilerplate corporate text with no ESRS data",
            page_offset=1,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=MagicMock(),
        )
        assert metrics == []

    def test_language_tag_from_manifest_propagates(
        self, good_metric_payload: dict[str, object]
    ) -> None:
        """If company.language is 'en', extracted metric.language is EN."""
        en_company = CompanyEntry(
            ticker="SAN.PA",
            name="Sanofi",
            sector="Pharma",
            country="FR",
            ir_page_url="https://www.sanofi.com/en/investors",
            language="en",
        )
        anthropic = MagicMock()
        anthropic.messages.create.return_value = _claude_tool_response([good_metric_payload])

        metrics = extract_esrs_metrics(
            pdf_text=good_metric_payload["source_snippet"],  # type: ignore[arg-type]
            page_offset=42,
            company=en_company,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=MagicMock(),
        )
        assert metrics[0].language == Language.EN


# ── Fallback to Mistral ──────────────────────────────────────────────


class TestMistralFallback:
    def test_claude_raises_falls_back_to_mistral(
        self, lvmh: CompanyEntry, good_metric_payload: dict[str, object]
    ) -> None:
        anthropic = MagicMock()
        anthropic.messages.create.side_effect = RuntimeError("Anthropic API down")

        mistral = MagicMock()
        mistral.chat.complete.return_value = _mistral_response([good_metric_payload])

        metrics = extract_esrs_metrics(
            pdf_text=good_metric_payload["source_snippet"],  # type: ignore[arg-type]
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=mistral,
        )

        assert len(metrics) == 1
        assert metrics[0].extraction_model == ExtractionModel.MISTRAL_LARGE
        mistral.chat.complete.assert_called_once()

    def test_claude_returns_invalid_payload_falls_back_to_mistral(
        self, lvmh: CompanyEntry, good_metric_payload: dict[str, object]
    ) -> None:
        """Claude returns a metric missing required fields → fallback."""
        anthropic = MagicMock()
        bad_payload = {"esrs_disclosure": "E1-6"}  # missing nearly everything
        anthropic.messages.create.return_value = _claude_tool_response([bad_payload])

        mistral = MagicMock()
        mistral.chat.complete.return_value = _mistral_response([good_metric_payload])

        metrics = extract_esrs_metrics(
            pdf_text=good_metric_payload["source_snippet"],  # type: ignore[arg-type]
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=mistral,
        )
        assert len(metrics) == 1
        assert metrics[0].extraction_model == ExtractionModel.MISTRAL_LARGE


# ── Both fail ────────────────────────────────────────────────────────


class TestBothFail:
    def test_both_clients_raise_propagates_extraction_error(self, lvmh: CompanyEntry) -> None:
        anthropic = MagicMock()
        anthropic.messages.create.side_effect = RuntimeError("anthropic down")
        mistral = MagicMock()
        mistral.chat.complete.side_effect = RuntimeError("mistral down")

        with pytest.raises(ExtractionError):
            extract_esrs_metrics(
                pdf_text="any",
                page_offset=1,
                company=lvmh,
                esrs_topic=ESRSTopic.E1_CLIMATE,
                fiscal_year=2024,
                anthropic_client=anthropic,
                mistral_client=mistral,
            )


# ── Source-citation handling ─────────────────────────────────────────


class TestSourceCitation:
    def test_source_page_uses_llm_value_directly(
        self, lvmh: CompanyEntry, good_metric_payload: dict[str, object]
    ) -> None:
        """The LLM reports the absolute page; we trust it (it sees page numbers in chunk)."""
        anthropic = MagicMock()
        anthropic.messages.create.return_value = _claude_tool_response([good_metric_payload])

        metrics = extract_esrs_metrics(
            pdf_text=good_metric_payload["source_snippet"],  # type: ignore[arg-type]
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=MagicMock(),
        )
        assert metrics[0].source_citation.page == 42
        assert good_metric_payload["source_snippet"] in metrics[0].source_citation.snippet  # type: ignore[operator]


# ── Disclosure-code normalization (regression for real-LLM run) ──────


class TestDisclosureCodeNormalization:
    """Real LLMs occasionally emit dotted sub-codes (e.g. 'E1-6.scope_2_location').

    These are internal to the prompt catalog — they would (a) overflow the
    schema's 20-char cap on esrs_disclosure, and (b) never join to dim_metric
    (which uses canonical parent codes). The build path strips the suffix.
    """

    def test_dotted_subcode_normalized_to_parent(self, lvmh: CompanyEntry) -> None:
        anthropic = MagicMock()
        payload = {
            "esrs_disclosure": "E1-6.scope_2_location",
            "metric_name": "Total Scope 2 GHG emissions (location-based)",
            "value_numeric": 88200.0,
            "value_text": None,
            "unit": "tCO2e",
            "model_confidence": 0.91,
            "source_page": 42,
            "source_snippet": "Location-based Scope 2 emissions reached 88,200 tCO2e in 2024.",
        }
        anthropic.messages.create.return_value = _claude_tool_response([payload])

        metrics = extract_esrs_metrics(
            pdf_text=str(payload["source_snippet"]),
            page_offset=42,
            company=lvmh,
            esrs_topic=ESRSTopic.E1_CLIMATE,
            fiscal_year=2024,
            anthropic_client=anthropic,
            mistral_client=MagicMock(),
        )
        assert len(metrics) == 1
        assert metrics[0].esrs_disclosure == "E1-6"
        # Disambiguation preserved in metric_name where dim_metric expects it.
        assert "location-based" in metrics[0].metric_name.lower()
