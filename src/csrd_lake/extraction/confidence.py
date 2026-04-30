"""Confidence scoring for ESRS metric extractions.

Maps four observable signals → a single confidence score in [0.0, 1.0]:

1. **logprob** — the LLM's reported logprob for the extracted value (≤ 0)
2. **structural_pass** — Pydantic validation succeeded
3. **snippet_match** — source_citation.snippet contains the extracted value
4. **language_match** — detected PDF language matches the metric's `language` field

Below the 0.80 threshold (configurable via env), values route to
`mart_disclosure_review_queue` instead of `mart_disclosure_published`
(PRD Story 4).

Pure function: deterministic given inputs. No I/O. Fully unit-testable.
"""


def compute_confidence(
    logprob: float,
    structural_pass: bool,
    snippet_match: bool,
    language_match: bool,
) -> float:
    """Compute a per-metric confidence score.

    Args:
        logprob: LLM-reported logprob for the extracted value. Always ≤ 0
            in practice; outliers are clamped.
        structural_pass: Did the Pydantic schema validate the extraction?
        snippet_match: Does `source_citation.snippet` literally contain the
            extracted value (numeric or text)?
        language_match: Does `langdetect` on the source PDF agree with the
            metric's claimed language (FR / EN)?

    Returns:
        A confidence score in [0.0, 1.0], rounded to 3 decimal places.
        Routing rule: scores < 0.80 land in the human-review queue.

    Examples:
        >>> compute_confidence(-0.1, True, True, True)
        1.0
        >>> compute_confidence(-0.1, False, True, True)
        0.0
        >>> 0.30 <= compute_confidence(-3.0, True, True, True) <= 0.50
        True
    """
    # Pydantic validation failure → score is zero. The value is unreliable
    # at the type level; further weighting would be misleading.
    if not structural_pass:
        return 0.0

    # Normalize logprob (typically [-5, 0]) to roughly [0, 1].
    # logprob = 0 → base = 1.0; logprob = -5 → base = 0.0; clamped outside.
    base = (logprob + 5.0) / 5.0
    base = max(0.0, min(1.0, base))

    # Source-citation mismatch is a strong negative signal: if we can't find
    # the value in the cited snippet, the LLM may have hallucinated or the
    # page-extraction was wrong. Penalize 50%.
    if not snippet_match:
        base *= 0.5

    # Language mismatch is a softer signal — could be a multilingual PDF
    # where the per-section language differs from the document-level claim.
    # Penalize 30%.
    if not language_match:
        base *= 0.7

    # Round to 3 decimals: matches Snowflake fact_disclosure.confidence_score
    # column scale and avoids float-trail artefacts in dashboards.
    return round(base, 3)
