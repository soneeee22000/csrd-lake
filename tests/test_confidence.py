"""Tests for confidence scoring (pure deterministic logic, no I/O).

PRD Story 4 acceptance: every extracted metric carries a confidence_score in [0, 1].
Below 0.80 routes to mart_disclosure_review_queue instead of mart_disclosure_published.

Confidence is deterministic given (logprob, structural_pass, snippet_match, language_match).
Tests cover all branches of the scoring function.
"""

import pytest

from csrd_lake.extraction.confidence import compute_confidence


class TestComputeConfidence:
    """Deterministic confidence scoring — fully unit-testable, no I/O."""

    def test_perfect_extraction_scores_high(self) -> None:
        """Strong logprob + all checks pass → confidence near 1.0."""
        score = compute_confidence(
            logprob=-0.1,  # very confident token
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        assert score >= 0.95
        assert score <= 1.0

    def test_low_logprob_drives_score_down(self) -> None:
        """Weak logprob lowers confidence even when checks pass."""
        score = compute_confidence(
            logprob=-3.0,  # weakly confident
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        assert 0.30 <= score <= 0.50

    def test_failed_structural_validation_zeros_confidence(self) -> None:
        """Pydantic validation failure means we cannot trust the value at all."""
        score = compute_confidence(
            logprob=-0.1,  # otherwise perfect
            structural_pass=False,
            snippet_match=True,
            language_match=True,
        )
        assert score == 0.0

    def test_snippet_mismatch_halves_confidence(self) -> None:
        """If the source citation doesn't contain the value, we trust it half as much."""
        with_match = compute_confidence(
            logprob=-0.5,
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        without_match = compute_confidence(
            logprob=-0.5,
            structural_pass=True,
            snippet_match=False,
            language_match=True,
        )
        assert without_match == pytest.approx(with_match * 0.5, abs=0.01)

    def test_language_mismatch_reduces_confidence(self) -> None:
        """If detected language doesn't match the claim, confidence drops 30%."""
        with_match = compute_confidence(
            logprob=-0.5,
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        without_match = compute_confidence(
            logprob=-0.5,
            structural_pass=True,
            snippet_match=True,
            language_match=False,
        )
        assert without_match == pytest.approx(with_match * 0.7, abs=0.01)

    def test_below_threshold_when_all_soft_checks_fail(self) -> None:
        """Both snippet + language fail with weak logprob → falls below 0.80 threshold."""
        score = compute_confidence(
            logprob=-2.0,
            structural_pass=True,
            snippet_match=False,
            language_match=False,
        )
        assert score < 0.80

    def test_score_clamped_to_unit_interval(self) -> None:
        """Score is always in [0.0, 1.0] regardless of logprob outliers."""
        very_high = compute_confidence(
            logprob=10.0,  # impossibly high (logprobs are <= 0)
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        very_low = compute_confidence(
            logprob=-100.0,  # absurdly low
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        assert 0.0 <= very_high <= 1.0
        assert 0.0 <= very_low <= 1.0

    def test_score_rounded_to_three_decimals(self) -> None:
        """Confidence stored at 3 decimal precision (matches Snowflake fact column scale)."""
        score = compute_confidence(
            logprob=-0.7,
            structural_pass=True,
            snippet_match=True,
            language_match=True,
        )
        # Verify it rounds cleanly — no float-trail artefacts
        assert score == round(score, 3)

    def test_deterministic_given_same_inputs(self) -> None:
        """Same inputs always produce same output (no randomness, no time-dependence)."""
        score1 = compute_confidence(-0.5, True, True, True)
        score2 = compute_confidence(-0.5, True, True, True)
        score3 = compute_confidence(-0.5, True, True, True)
        assert score1 == score2 == score3

    @pytest.mark.parametrize(
        "logprob,structural,snippet,language,expected_below_threshold",
        [
            (-0.1, True, True, True, False),  # all good → ~1.0, above
            (-0.1, False, True, True, True),  # structural fail → 0.0, below
            (-0.1, True, False, True, True),  # snippet fail halves to ~0.49, below
            (-2.0, True, True, False, True),  # weak + lang fail → below
            (-5.0, True, True, True, True),  # very weak → 0.0, below
            (-0.5, True, True, True, False),  # solid logprob, all checks → ~0.9, above
        ],
    )
    def test_threshold_routing(
        self,
        logprob: float,
        structural: bool,
        snippet: bool,
        language: bool,
        expected_below_threshold: bool,
    ) -> None:
        """Threshold of 0.80 cleanly separates routing decisions per PRD Story 4."""
        score = compute_confidence(logprob, structural, snippet, language)
        is_below = score < 0.80
        assert is_below == expected_below_threshold, (
            f"score={score} for inputs ({logprob}, {structural}, {snippet}, {language})"
        )
