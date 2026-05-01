"""End-to-end LLM extraction smoke test.

Runs the real `extract_esrs_metrics` pipeline against ONE real PDF using
the real Anthropic + Mistral APIs. Prints every extracted ESRSMetric with
its confidence score, source citation, and routing decision.

Usage:
    python -m csrd_lake.extraction.cli --pdf data/samples/lvmh-sr-2024.pdf
    python -m csrd_lake.extraction.cli --pdf x.pdf --ticker TTE.PA --topic E1
    make verify-llm PDF=data/samples/x.pdf

Environment variables (read from .env via python-dotenv):
    ANTHROPIC_API_KEY  — required
    MISTRAL_API_KEY    — required
    ANTHROPIC_MODEL    — optional override (default: claude-sonnet-4-6)
    MISTRAL_MODEL      — optional override (default: mistral-large-latest)
    MAX_PDF_PAGES      — optional, truncate PDF read (default: 200)

Cost estimate: ~$0.05-$0.15 per run on a 200-page PDF (Claude Sonnet input
pricing dominates). Mistral fallback only fires if Claude errors.

Exit codes:
    0  — extraction succeeded (≥0 metrics returned)
    1  — missing API key or PDF
    2  — PDF parse error
    3  — extraction error (both LLMs failed)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import structlog
from anthropic import Anthropic
from dotenv import load_dotenv
from mistralai.client import Mistral

from csrd_lake.extraction.llm import ExtractionError, extract_esrs_metrics
from csrd_lake.extraction.schemas import ESRSMetric, ESRSTopic
from csrd_lake.ingestion.manifest import CAC40_MANIFEST_PATH, load_manifest

logger = structlog.get_logger(__name__)


def _read_pdf_text(pdf_path: Path, max_pages: int) -> tuple[str, int]:
    """Return (text, page_count) from a PDF. Caps at max_pages for cost control."""
    import pdfplumber  # local import — heavy

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = min(len(pdf.pages), max_pages)
        for i, page in enumerate(pdf.pages[:page_count]):
            text = page.extract_text() or ""
            parts.append(f"[page {i + 1}]\n{text}")
    return "\n\n".join(parts), page_count


def _print_metric(m: ESRSMetric) -> None:
    """Pretty-print one ESRSMetric to stdout."""
    value = m.value_numeric if m.value_numeric is not None else m.value_text
    routing = "PUBLISHED" if m.confidence_score >= 0.80 else "REVIEW_QUEUE"
    print(f"  • {m.esrs_disclosure} — {m.metric_name}")
    print(f"      value:      {value} {m.unit or ''}")
    print(f"      confidence: {m.confidence_score:.3f}  →  {routing}")
    print(f"      model:      {m.extraction_model.value}")
    print(
        f"      source:     p.{m.source_citation.page} — "
        f'"{m.source_citation.snippet[:100]}{"…" if len(m.source_citation.snippet) > 100 else ""}"'
    )
    print()


def _summarize(metrics: list[ESRSMetric]) -> None:
    """Print a one-screen routing + model breakdown."""
    if not metrics:
        print("\n  No metrics extracted. Possible causes:")
        print("    - LLM did not find any of the catalogued metrics in the chunk")
        print("    - PDF is image-only (extract_text returned empty)")
        print("    - Topic mismatch (e.g. requesting E3 from a workforce-heavy chapter)")
        return
    published = sum(1 for m in metrics if m.confidence_score >= 0.80)
    review = len(metrics) - published
    by_model: dict[str, int] = {}
    for m in metrics:
        by_model[m.extraction_model.value] = by_model.get(m.extraction_model.value, 0) + 1
    print("─" * 72)
    print(f"  Total extracted:           {len(metrics)}")
    print(f"  Routed to published mart:  {published}  ({100 * published / len(metrics):.0f}%)")
    print(f"  Routed to review queue:    {review}  ({100 * review / len(metrics):.0f}%)")
    print("  By extraction model:")
    for model, count in sorted(by_model.items()):
        print(f"    - {model}: {count}")
    avg_conf = sum(m.confidence_score for m in metrics) / len(metrics)
    print(f"  Average confidence:        {avg_conf:.3f}")


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="End-to-end LLM extraction smoke test against one real PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        required=True,
        help="Path to a corporate sustainability PDF (e.g. data/samples/lvmh-2024.pdf).",
    )
    parser.add_argument(
        "--ticker",
        default="MC.PA",
        help="Company ticker from the manifest. Default: MC.PA (LVMH).",
    )
    parser.add_argument(
        "--topic",
        default="E1",
        choices=["E1", "E2", "E3", "S1", "G1"],
        help="ESRS topic to extract. Default: E1 (climate change).",
    )
    parser.add_argument("--fiscal-year", type=int, default=2024)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.environ.get("MAX_PDF_PAGES", "200")),
        help="Truncate PDF after N pages for cost control. Default: 200.",
    )
    args = parser.parse_args()

    # ── Sanity: API keys ─────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Add to .env or export.", file=sys.stderr)
        return 1
    if not os.environ.get("MISTRAL_API_KEY"):
        print("ERROR: MISTRAL_API_KEY not set. Add to .env or export.", file=sys.stderr)
        return 1
    if not args.pdf.exists():
        print(f"ERROR: PDF not found at {args.pdf}", file=sys.stderr)
        return 1

    # ── Find company in manifest ──────────────────────────────────────
    manifest = load_manifest(CAC40_MANIFEST_PATH)
    company = next((c for c in manifest.companies if c.ticker == args.ticker), None)
    if company is None:
        tickers = ", ".join(c.ticker for c in manifest.companies)
        print(
            f"ERROR: Ticker '{args.ticker}' not in manifest. Known: {tickers}",
            file=sys.stderr,
        )
        return 1

    # ── Read PDF ──────────────────────────────────────────────────────
    print(f"\n→ Company:    {company.name} ({company.ticker})")
    print(f"→ Sector:     {company.sector}")
    print(f"→ Language:   {company.language}")
    print(f"→ PDF:        {args.pdf} ({args.pdf.stat().st_size / 1024:.1f} KB)")
    print(f"→ Topic:      {args.topic}")
    print(f"→ Year:       FY{args.fiscal_year}")

    try:
        pdf_text, pages_read = _read_pdf_text(args.pdf, args.max_pages)
    except Exception as exc:
        print(f"ERROR: Failed to parse PDF: {exc}", file=sys.stderr)
        return 2

    print(f"→ PDF text:   {len(pdf_text):,} chars from {pages_read} pages\n")

    # ── Call extraction ──────────────────────────────────────────────
    print("→ Calling Claude Sonnet (primary), with Mistral Large fallback…\n")
    anthropic_client = Anthropic()
    mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    try:
        metrics = extract_esrs_metrics(
            pdf_text=pdf_text,
            page_offset=1,
            company=company,
            esrs_topic=ESRSTopic(args.topic),
            fiscal_year=args.fiscal_year,
            anthropic_client=anthropic_client,
            mistral_client=mistral_client,
        )
    except ExtractionError as exc:
        print(f"ERROR: Both LLMs failed — {exc}", file=sys.stderr)
        return 3

    # ── Print results ────────────────────────────────────────────────
    print(f"✓ Extracted {len(metrics)} metric(s) from topic {args.topic}\n")
    print("─" * 72)
    for m in metrics:
        _print_metric(m)
    _summarize(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
