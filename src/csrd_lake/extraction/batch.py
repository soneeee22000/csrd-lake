"""Batch extraction runner — runs LLM extraction across all PDFs in data/raw/
and all 5 ESRS topics, persists per-company JSON archives, and lands results
into the local DuckDB warehouse.

Usage:
    python -m csrd_lake.extraction.batch
    python -m csrd_lake.extraction.batch --max-pages 150 --duckdb data/warehouse/csrd_lake.duckdb

Behavior:
  - Discovers PDFs at data/raw/{ticker}-{fiscal_year}.pdf using the manifest.
  - For each (company, topic): extracts via Claude→Mistral fallback chain,
    accumulates ESRSMetric instances.
  - Persists per-company JSON to data/extracted/{ticker}-{fiscal_year}.json.
  - Truncates raw.disclosure_extracted then bulk-inserts the full set so re-runs
    yield a deterministic snapshot.
  - Prints a one-screen routing + cost summary at the end.

Cost estimate: ~$0.05-$0.15 per (PDF x topic) call. 3 PDFs x 5 topics ~= $1-3.

Exit codes:
    0  — completed (some topics may have been skipped if both LLMs failed; logged)
    1  — environment error (missing keys, no PDFs found)
    2  — extraction errored on >50% of attempts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog
from anthropic import Anthropic
from dotenv import load_dotenv
from mistralai.client import Mistral

from csrd_lake.extraction.cli import _read_pdf_text
from csrd_lake.extraction.llm import ExtractionError, extract_esrs_metrics
from csrd_lake.extraction.schemas import ESRSMetric, ESRSTopic
from csrd_lake.ingestion.manifest import CAC40_MANIFEST_PATH, CompanyEntry, load_manifest
from csrd_lake.warehouse.duckdb_loader import DEFAULT_DUCKDB_PATH, bootstrap, load_metrics

logger = structlog.get_logger(__name__)


@dataclass
class TopicResult:
    """Per (company, topic) attempt outcome."""

    ticker: str
    topic: str
    metrics: list[ESRSMetric]
    error: str | None


# Per-topic keywords used to filter pages before sending to the LLM. Keeps
# the prompt under the 30K input-tokens-per-minute Anthropic free-tier limit
# while preserving topic-relevant content (typically ~30-60 pages of a 200-
# page sustainability report match a given topic).
TOPIC_KEYWORDS: dict[ESRSTopic, list[str]] = {
    ESRSTopic.E1_CLIMATE: [
        "scope 1",
        "scope 2",
        "scope 3",
        "ghg",
        "greenhouse gas",
        "tco2",
        "co2e",
        "co₂e",
        "co2 e",
        "net-zero",
        "net zero",
        "climate",
        "esrs e1",
        "energy consumption",
        "renewable",
        "transition plan",
    ],
    ESRSTopic.E2_POLLUTION: [
        "air pollutant",
        "voc",
        "nox",
        "sox",
        "particulate",
        "pollutant",
        "substances of concern",
        "esrs e2",
        "soil contamination",
    ],
    ESRSTopic.E3_WATER: [
        "water consumption",
        "water withdrawal",
        "water-stress",
        "water stress",
        "freshwater",
        "esrs e3",
        "water discharge",
    ],
    ESRSTopic.S1_WORKFORCE: [
        "headcount",
        "employees",
        "workforce",
        "fatalities",
        "injuries",
        "lost-time",
        "gender",
        "pay gap",
        "esrs s1",
        "diversity",
        "training hours",
    ],
    ESRSTopic.G1_GOVERNANCE: [
        "business conduct",
        "code of conduct",
        "corruption",
        "bribery",
        "whistleblower",
        "esrs g1",
        "ethics",
        "anti-corruption",
        "lobbying",
        "political contribution",
    ],
}

# Page header pattern emitted by `_read_pdf_text` (e.g. "[page 42]").
_PAGE_HEADER = re.compile(r"\[page (\d+)\]")


def filter_pages_by_topic(pdf_text: str, topic: ESRSTopic, max_chars: int) -> str:
    """Return only pages that mention any of the topic's keywords.

    Splits `pdf_text` (produced by `_read_pdf_text`, which prefixes each page
    with `[page N]`), keeps pages whose lowercased text contains a topic
    keyword, then truncates to `max_chars`. If no pages match, returns the
    first `max_chars` of the original text as a fallback.
    """
    keywords = TOPIC_KEYWORDS.get(topic, [])
    pages: list[tuple[int, str]] = []
    matches = list(_PAGE_HEADER.finditer(pdf_text))
    for idx, match in enumerate(matches):
        page_num = int(match.group(1))
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(pdf_text)
        chunk = pdf_text[match.start() : end]
        pages.append((page_num, chunk))
    selected: list[str] = []
    total = 0
    for _, chunk in pages:
        lower = chunk.lower()
        if any(k in lower for k in keywords):
            if total + len(chunk) > max_chars:
                break
            selected.append(chunk)
            total += len(chunk)
    if not selected:
        return pdf_text[:max_chars]
    return "\n\n".join(selected)


def _discover_pdfs(
    manifest_companies: list[CompanyEntry],
    raw_dir: Path,
    fiscal_year: int,
) -> list[tuple[CompanyEntry, Path]]:
    """Return (company, pdf_path) for every manifest entry with a downloaded PDF."""
    out: list[tuple[CompanyEntry, Path]] = []
    for company in manifest_companies:
        candidate = raw_dir / f"{company.ticker}-{fiscal_year}.pdf"
        if candidate.exists():
            out.append((company, candidate))
    return out


def _persist_json(metrics: list[ESRSMetric], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [m.model_dump(mode="json") for m in metrics]
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _truncate_raw(conn: object) -> None:
    """Wipe the raw landing table for a deterministic snapshot."""
    conn.execute("DELETE FROM raw.disclosure_extracted")  # type: ignore[attr-defined]


def _print_summary(results: list[TopicResult], duckdb_count: int, started: datetime) -> None:
    elapsed = (datetime.now(UTC) - started).total_seconds()
    total_attempts = len(results)
    successful = [r for r in results if r.error is None]
    extracted = sum(len(r.metrics) for r in successful)
    published = sum(1 for r in successful for m in r.metrics if m.confidence_score >= 0.80)
    review = extracted - published

    print()
    print("=" * 72)
    print("BATCH EXTRACTION SUMMARY")
    print("=" * 72)
    print(f"  Elapsed:                {elapsed:.1f}s")
    print(f"  Topics attempted:       {total_attempts}")
    print(f"  Topics succeeded:       {len(successful)}")
    print(f"  Total metrics:          {extracted}")
    print(f"  Routed to published:    {published} ({100 * published / max(extracted, 1):.0f}%)")
    print(f"  Routed to review:       {review} ({100 * review / max(extracted, 1):.0f}%)")
    print(f"  Rows in DuckDB:         {duckdb_count}")
    print()
    print("Per company x topic:")
    by_ticker: dict[str, list[TopicResult]] = {}
    for r in results:
        by_ticker.setdefault(r.ticker, []).append(r)
    for ticker, topic_results in by_ticker.items():
        for r in topic_results:
            badge = "ok " if r.error is None else "ERR"
            count = len(r.metrics) if r.error is None else 0
            err = f" — {r.error}" if r.error else ""
            print(f"  [{badge}] {ticker} {r.topic}: {count} metric(s){err}")
    print()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fiscal-year", type=int, default=2024)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.environ.get("MAX_PDF_PAGES", "200")),
        help="Truncate PDFs after N pages for cost control.",
    )
    parser.add_argument(
        "--duckdb",
        type=Path,
        default=DEFAULT_DUCKDB_PATH,
        help="Path to the DuckDB warehouse file.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing downloaded sustainability PDFs.",
    )
    parser.add_argument(
        "--extracted-dir",
        type=Path,
        default=Path("data/extracted"),
        help="Directory for per-company JSON archives.",
    )
    parser.add_argument(
        "--max-prompt-chars",
        type=int,
        default=80_000,
        help="After topic-keyword filtering, cap each prompt's report excerpt at N chars (~20K tokens). Tune for your LLM rate limit.",
    )
    parser.add_argument(
        "--inter-call-delay",
        type=float,
        default=0.0,
        help="Seconds to sleep between (PDF, topic) calls. Set to 12+ if hitting the 30K-tokens-per-minute Anthropic free tier.",
    )
    args = parser.parse_args()

    # ── Sanity ────────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("MISTRAL_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY and MISTRAL_API_KEY must be set.", file=sys.stderr)
        return 1

    manifest = load_manifest(CAC40_MANIFEST_PATH)
    pdfs = _discover_pdfs(manifest.companies, args.raw_dir, args.fiscal_year)
    if not pdfs:
        print(f"ERROR: No PDFs found in {args.raw_dir}/. Run ingestion first.", file=sys.stderr)
        return 1

    print(f"→ Manifest:        {len(manifest.companies)} companies")
    print(f"→ PDFs on disk:    {len(pdfs)}")
    print(f"→ Topics:          {len(ESRSTopic)} ({', '.join(t.value for t in ESRSTopic)})")
    print(f"→ Total attempts:  {len(pdfs) * len(ESRSTopic)}")
    print(f"→ Max pages:       {args.max_pages}")
    print(f"→ DuckDB target:   {args.duckdb}")
    print()

    started = datetime.now(UTC)
    anthropic_client = Anthropic()
    mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    # Open DuckDB once and stream metrics in per-topic so a mid-batch crash
    # never loses work. The dbt staging layer dedupes on natural key + recency.
    conn = bootstrap(args.duckdb)
    _truncate_raw(conn)

    all_metrics: list[ESRSMetric] = []
    results: list[TopicResult] = []
    try:
        for company, pdf_path in pdfs:
            print(f"━━ {company.ticker} {company.name} ({pdf_path.name})")
            pdf_text, pages_read = _read_pdf_text(pdf_path, args.max_pages)
            print(f"   read {len(pdf_text):,} chars from {pages_read} pages")
            company_metrics: list[ESRSMetric] = []
            for topic_idx, topic in enumerate(ESRSTopic):
                if topic_idx > 0 and args.inter_call_delay > 0:
                    time.sleep(args.inter_call_delay)
                topic_text = filter_pages_by_topic(pdf_text, topic, args.max_prompt_chars)
                try:
                    topic_metrics = extract_esrs_metrics(
                        pdf_text=topic_text,
                        page_offset=1,
                        company=company,
                        esrs_topic=topic,
                        fiscal_year=args.fiscal_year,
                        anthropic_client=anthropic_client,
                        mistral_client=mistral_client,
                    )
                    if topic_metrics:
                        load_metrics(topic_metrics, conn=conn)
                    company_metrics.extend(topic_metrics)
                    all_metrics.extend(topic_metrics)
                    results.append(TopicResult(company.ticker, topic.value, topic_metrics, None))
                    print(f"   {topic.value}: {len(topic_metrics)} metric(s)")
                except ExtractionError as exc:
                    results.append(TopicResult(company.ticker, topic.value, [], str(exc)))
                    print(f"   {topic.value}: FAILED — {exc}")
            out_path = args.extracted_dir / f"{company.ticker}-{args.fiscal_year}.json"
            _persist_json(company_metrics, out_path)
            print(f"   archived → {out_path} ({len(company_metrics)} metrics)")
            print()

        duckdb_count = conn.execute("SELECT COUNT(*) FROM raw.disclosure_extracted").fetchone()[0]
    finally:
        conn.close()

    _print_summary(results, duckdb_count, started)

    failed = sum(1 for r in results if r.error is not None)
    return 2 if failed > len(results) // 2 else 0


if __name__ == "__main__":
    sys.exit(main())
