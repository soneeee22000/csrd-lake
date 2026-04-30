"""LLM extraction layer — Claude Sonnet primary + Mistral Large fallback.

Public entrypoint: `extract_esrs_metrics(...)`.

Both LLMs are called via dependency injection so tests can mock them.
The fallback chain handles:
- API errors (network, auth, rate limit)
- Malformed structured outputs (Pydantic validation fails)
- Empty / off-topic responses

Per PRD Story 4: every returned `ESRSMetric` carries a `confidence_score` in
[0, 1] and a `source_citation` with page + verbatim snippet.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import ValidationError

from csrd_lake.extraction.confidence import compute_confidence
from csrd_lake.extraction.prompts import (
    EXTRACTION_TOOL_SCHEMA,
    build_extraction_prompt,
)
from csrd_lake.extraction.schemas import (
    ESRSMetric,
    ESRSTopic,
    ExtractionModel,
    Language,
    SourceCitation,
)

if TYPE_CHECKING:
    from csrd_lake.ingestion.manifest import CompanyEntry

logger = structlog.get_logger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"
MISTRAL_MODEL = "mistral-large-latest"


class ExtractionError(Exception):
    """Raised when both Claude and Mistral fail to produce valid extractions."""


# ── Public entrypoint ─────────────────────────────────────────────────


def extract_esrs_metrics(
    *,
    pdf_text: str,
    page_offset: int,
    company: CompanyEntry,
    esrs_topic: ESRSTopic,
    fiscal_year: int,
    anthropic_client: Any,
    mistral_client: Any,
) -> list[ESRSMetric]:
    """Extract ESRS metrics from a PDF text chunk.

    Args:
        pdf_text: The chunk of PDF text to extract from.
        page_offset: 1-indexed start page of the chunk in the source PDF
            (currently used for logging only; the LLM reports absolute pages).
        company: The company manifest entry (provides ticker, name, language).
        esrs_topic: Which ESRS topic to extract (E1, E2, E3, S1, G1).
        fiscal_year: Reporting year stamped on the extracted metrics.
        anthropic_client: An Anthropic client (real or mocked).
        mistral_client: A Mistral client (real or mocked).

    Returns:
        List of validated `ESRSMetric` (may be empty if no metrics found).

    Raises:
        ExtractionError: Both Claude and Mistral failed to produce valid output.
    """
    prompt = build_extraction_prompt(
        pdf_text=pdf_text,
        company_name=company.name,
        fiscal_year=fiscal_year,
        esrs_topic=esrs_topic,
        language=company.language,
    )

    # ── Attempt Claude (primary) ──────────────────────────────────────
    try:
        raw = _call_claude(anthropic_client, prompt)
        metrics = _build_metrics(
            raw,
            company=company,
            esrs_topic=esrs_topic,
            fiscal_year=fiscal_year,
            page_offset=page_offset,
            extraction_model=ExtractionModel.CLAUDE_SONNET_4_6,
        )
        logger.info(
            "extraction.claude.success",
            company=company.ticker,
            topic=esrs_topic.value,
            count=len(metrics),
        )
        return metrics
    except (RuntimeError, ValidationError, ValueError, KeyError) as exc:
        logger.warning(
            "extraction.claude.failed",
            company=company.ticker,
            topic=esrs_topic.value,
            error=str(exc),
        )

    # ── Fall back to Mistral ──────────────────────────────────────────
    try:
        raw = _call_mistral(mistral_client, prompt)
        metrics = _build_metrics(
            raw,
            company=company,
            esrs_topic=esrs_topic,
            fiscal_year=fiscal_year,
            page_offset=page_offset,
            extraction_model=ExtractionModel.MISTRAL_LARGE,
        )
        logger.info(
            "extraction.mistral.success",
            company=company.ticker,
            topic=esrs_topic.value,
            count=len(metrics),
        )
        return metrics
    except (RuntimeError, ValidationError, ValueError, KeyError) as exc:
        logger.error(
            "extraction.mistral.failed",
            company=company.ticker,
            topic=esrs_topic.value,
            error=str(exc),
        )
        raise ExtractionError(
            f"Both Claude and Mistral failed for {company.ticker}/{esrs_topic.value}"
        ) from exc


# ── Per-LLM call adapters ─────────────────────────────────────────────


def _call_claude(client: Any, prompt: str) -> dict[str, Any]:
    """Call Claude via tool-use to force structured output. Returns the tool input dict."""
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        tools=[
            {
                "name": "extract_esrs_metrics",
                "description": "Return the ESRS metrics extracted from the report excerpt.",
                "input_schema": EXTRACTION_TOOL_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "extract_esrs_metrics"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            value = block.input
            if not isinstance(value, dict):
                raise ValueError(f"Claude tool_use input is not a dict: {type(value).__name__}")
            return value

    raise ValueError("Claude response had no tool_use block")


def _call_mistral(client: Any, prompt: str) -> dict[str, Any]:
    """Call Mistral with JSON object response_format. Returns the parsed dict."""
    response = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\nReturn a JSON object matching this schema:\n"
                    f"{json.dumps(EXTRACTION_TOOL_SCHEMA, indent=2)}"
                ),
            }
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError(f"Mistral content is not a string: {type(content).__name__}")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"Mistral JSON is not an object: {type(parsed).__name__}")
    return parsed


# ── Build validated ESRSMetric instances from raw LLM payload ─────────


def _build_metrics(
    raw: dict[str, Any],
    *,
    company: CompanyEntry,
    esrs_topic: ESRSTopic,
    fiscal_year: int,
    page_offset: int,
    extraction_model: ExtractionModel,
) -> list[ESRSMetric]:
    """Validate the LLM payload, compute confidence, return ESRSMetric list.

    Raises ValidationError if any individual metric fails the schema —
    callers (the extract_esrs_metrics fallback chain) translate that to a
    fallback trigger.
    """
    items = raw.get("metrics", [])
    if not isinstance(items, list):
        raise ValueError(f"Expected 'metrics' to be a list, got {type(items).__name__}")

    out: list[ESRSMetric] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"Each metric must be a dict, got {type(item).__name__}")

        # Self-rated model confidence → pseudo-logprob for compute_confidence.
        # Map [0, 1] → roughly [-5, 0]: 1.0 → 0, 0.0 → -5.0.
        model_conf = float(item.get("model_confidence", 0.5))
        pseudo_logprob = -5.0 * (1.0 - max(0.0, min(1.0, model_conf)))

        # Build the citation first (lets the snippet validator fire).
        citation = SourceCitation(
            page=int(item["source_page"]),
            snippet=str(item["source_snippet"]),
        )

        # Snippet match: does the snippet contain the value as written?
        value_numeric = item.get("value_numeric")
        value_text = item.get("value_text")
        snippet_match = _snippet_contains_value(
            citation.snippet,
            value_numeric=value_numeric,
            value_text=value_text,
        )

        # Language match: trust manifest claim for v1.
        # Future: cross-check via langdetect on the chunk.
        language_match = True

        confidence = compute_confidence(
            logprob=pseudo_logprob,
            structural_pass=True,  # if we got here, schema is valid
            snippet_match=snippet_match,
            language_match=language_match,
        )

        metric = ESRSMetric(
            company_ticker=company.ticker,
            fiscal_year=fiscal_year,
            esrs_topic=esrs_topic,
            esrs_disclosure=str(item["esrs_disclosure"]),
            metric_name=str(item["metric_name"]),
            value_numeric=float(value_numeric) if value_numeric is not None else None,
            value_text=str(value_text) if value_text is not None else None,
            unit=str(item["unit"]) if item.get("unit") is not None else None,
            confidence_score=confidence,
            source_citation=citation,
            language=Language(company.language),
            extraction_model=extraction_model,
        )
        out.append(metric)

    logger.debug(
        "extraction.built",
        company=company.ticker,
        topic=esrs_topic.value,
        page_offset=page_offset,
        count=len(out),
    )
    return out


def _snippet_contains_value(
    snippet: str,
    *,
    value_numeric: float | None,
    value_text: str | None,
) -> bool:
    """Lightweight check: does the source snippet contain the extracted value?

    For numerics, we accept either the raw number or its formatted version
    (commas, dots, spaces). For text, a case-insensitive substring match.
    """
    snippet_norm = snippet.replace(",", "").replace(" ", "").lower()

    if value_numeric is not None:
        # Try a few common renderings (147500 / 147,500 / 147 500 / 147.500)
        candidates = {
            f"{value_numeric:.0f}",
            f"{value_numeric:.1f}",
            f"{value_numeric:.2f}",
        }
        return any(c.replace(".", "").replace(",", "").lower() in snippet_norm for c in candidates)

    if value_text is not None:
        return value_text.lower() in snippet.lower()

    # Should never happen — Pydantic enforces exactly one of numeric/text.
    return False
