"""Pydantic v2 schemas for ESRS metric extraction.

Single source of truth for what an extracted ESRS metric looks like.
All LLM extraction outputs validate against these models — no raw dict parsing.

PRD Story 4 acceptance: every extracted metric has confidence_score + source_citation.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ESRSTopic(StrEnum):
    """ESRS topical standards (subset for v1; PRD §8 marks full set as out-of-scope)."""

    E1_CLIMATE = "E1"
    E2_POLLUTION = "E2"
    E3_WATER = "E3"
    S1_WORKFORCE = "S1"
    G1_GOVERNANCE = "G1"


class Language(StrEnum):
    """Languages supported in v1 (FR + EN). DE/ES out-of-scope per PRD §8."""

    FR = "fr"
    EN = "en"


class ExtractionModel(StrEnum):
    """LLMs used for extraction. Tracked for audit + per-model accuracy reporting."""

    CLAUDE_SONNET_4_7 = "claude-sonnet-4-7"
    MISTRAL_LARGE = "mistral-large-latest"


class SourceCitation(BaseModel):
    """Audit trail per extracted metric — page + snippet from source PDF."""

    page: int = Field(ge=1, description="1-indexed page number in source PDF")
    snippet: str = Field(
        min_length=20,
        max_length=500,
        description="Verbatim text from source PDF that supports the value",
    )

    @field_validator("snippet")
    @classmethod
    def snippet_not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("snippet must contain non-whitespace text")
        return v


class ESRSMetric(BaseModel):
    """One ESRS metric extracted from a corporate sustainability PDF.

    Either value_numeric OR value_text is populated, never both.
    """

    # Identity
    company_ticker: str = Field(min_length=2, max_length=10)
    fiscal_year: int = Field(ge=2020, le=2030)

    # ESRS taxonomy
    esrs_topic: ESRSTopic
    esrs_disclosure: str = Field(
        min_length=3,
        max_length=20,
        description="e.g. 'E1-1', 'E1-6', 'S1-7'",
    )
    metric_name: str = Field(min_length=3, max_length=200)

    # Value (exactly one populated)
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None

    # Audit + confidence
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Routes <0.80 to human review queue (PRD Story 4)",
    )
    source_citation: SourceCitation
    language: Language

    # Provenance
    extraction_model: ExtractionModel
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def exactly_one_value_populated(self) -> Self:
        """Enforce that exactly one of value_numeric or value_text is set.

        Field-level validators don't fire on default values in Pydantic v2,
        so this runs as a model-level validator after all fields are bound.
        """
        if self.value_numeric is None and self.value_text is None:
            raise ValueError("Either value_numeric or value_text must be populated")
        if self.value_numeric is not None and self.value_text is not None:
            raise ValueError("Only one of value_numeric or value_text may be populated, not both")
        return self
