"""End-to-end CSRD-Lake DAG.

Composes the pure-logic modules from `csrd_lake.*` into a single
TaskFlow-API DAG with three task groups:

  ingest  → download corporate sustainability PDFs (mapped per company)
  extract → call Claude (with Mistral fallback) for each ESRS topic per PDF
  load    → bulk-insert all extractions into Snowflake RAW.DISCLOSURE_EXTRACTED

The DAG uses dynamic task mapping (`.expand()`) so the per-company and
per-topic parallelism scales with the manifest without manual fan-out.

This file is the orchestration shell. All real logic lives in the pure
modules under `src/csrd_lake/` which are unit-tested in isolation. The DAG
is responsible for:
  - reading runtime config (data dir, env vars, Snowflake conn)
  - retry policy, scheduling, observability
  - serializing intermediate state via XCom (Pydantic .model_dump)

Run inside the Airflow Docker Compose stack defined at the project root.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from anthropic import Anthropic
from mistralai import Mistral

from airflow.decorators import dag, task, task_group
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from csrd_lake.extraction.llm import extract_esrs_metrics
from csrd_lake.extraction.schemas import ESRSMetric, ESRSTopic
from csrd_lake.ingestion.downloader import download_pdf
from csrd_lake.ingestion.manifest import (
    CAC40_MANIFEST_PATH,
    CompanyEntry,
    load_manifest,
)
from csrd_lake.warehouse.loader import load_metrics

logger = structlog.get_logger(__name__)

# ── Runtime paths (mounted into the Airflow container by docker-compose) ──
DATA_DIR = Path(os.environ.get("CSRD_DATA_DIR", "/opt/airflow/data"))
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"

# ── Default retry / observability policy for every task in the DAG ────
DEFAULT_TASK_ARGS = {
    "owner": "pyae",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# Reporting year is currently hardcoded — wave-1 CSRD is FY2024 reports.
# Override via Airflow Param if/when v2 ingests multiple fiscal years.
DEFAULT_FISCAL_YEAR = 2024


# ──────────────────────────────────────────────────────────────────────
# DAG definition
# ──────────────────────────────────────────────────────────────────────


@dag(
    dag_id="csrd_lake",
    description=(
        "End-to-end CSRD/ESRS pipeline: ingest sustainability PDFs, extract "
        "ESRS metrics with Claude+Mistral fallback, land in Snowflake."
    ),
    schedule=None,  # manual trigger v1; v2 may schedule quarterly
    start_date=datetime(2026, 4, 30),
    catchup=False,
    max_active_runs=1,
    tags=["csrd-lake", "esrs", "ingestion", "extraction"],
    default_args=DEFAULT_TASK_ARGS,
    doc_md=__doc__,
)
def csrd_lake_dag() -> None:
    # ── INGEST ────────────────────────────────────────────────────────
    @task_group(group_id="ingest")
    def ingest_group() -> Any:
        @task
        def list_companies() -> list[dict[str, Any]]:
            """Read the CAC 40 manifest and emit one row per company."""
            manifest = load_manifest(CAC40_MANIFEST_PATH)
            return [c.model_dump(mode="json") for c in manifest.companies]

        @task
        def download_one(company: dict[str, Any]) -> dict[str, Any]:
            """Download one company's latest sustainability PDF.

            Skips download if the PDF is already on disk (idempotent).
            Returns the company dict enriched with `pdf_path`.
            """
            entry = CompanyEntry.model_validate(company)
            url = (
                str(entry.known_report_url)
                if entry.known_report_url is not None
                else _scrape_latest_report_url(str(entry.ir_page_url))
            )
            target = RAW_DIR / f"{entry.ticker}-{DEFAULT_FISCAL_YEAR}.pdf"
            download_pdf(url, target)
            logger.info("ingest.downloaded", ticker=entry.ticker, target=str(target))
            return {**company, "pdf_path": str(target), "report_url": url}

        return download_one.expand(company=list_companies())

    # ── EXTRACT ───────────────────────────────────────────────────────
    @task_group(group_id="extract")
    def extract_group(downloaded: list[dict[str, Any]]) -> Any:
        @task
        def extract_one(payload: dict[str, Any]) -> str:
            """Run LLM extraction across all 5 ESRS topics for one company.

            Persists the metrics to a JSON file so the load task can read them
            without needing to fit a large XCom payload.
            """
            entry = CompanyEntry.model_validate(payload)
            pdf_path = Path(payload["pdf_path"])
            pdf_text = _read_pdf_text(pdf_path)

            anthropic_client = Anthropic()  # picks up ANTHROPIC_API_KEY
            mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

            all_metrics: list[ESRSMetric] = []
            for topic in ESRSTopic:
                try:
                    chunk_metrics = extract_esrs_metrics(
                        pdf_text=pdf_text,
                        page_offset=1,
                        company=entry,
                        esrs_topic=topic,
                        fiscal_year=DEFAULT_FISCAL_YEAR,
                        anthropic_client=anthropic_client,
                        mistral_client=mistral_client,
                    )
                    all_metrics.extend(chunk_metrics)
                except Exception as exc:
                    # One topic failing should not nuke the whole company —
                    # log and move on. Downstream dbt tests catch coverage gaps.
                    logger.error(
                        "extract.topic.failed",
                        ticker=entry.ticker,
                        topic=topic.value,
                        error=str(exc),
                    )

            EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
            out_path = EXTRACTED_DIR / f"{entry.ticker}-{DEFAULT_FISCAL_YEAR}.json"
            out_path.write_text(
                json.dumps([m.model_dump(mode="json") for m in all_metrics], default=str),
                encoding="utf-8",
            )
            logger.info(
                "extract.success",
                ticker=entry.ticker,
                metric_count=len(all_metrics),
                out=str(out_path),
            )
            return str(out_path)

        return extract_one.expand(payload=downloaded)

    # ── LOAD ──────────────────────────────────────────────────────────
    @task_group(group_id="load")
    def load_group(extracted_paths: list[str]) -> None:
        @task
        def load_one(extracted_path: str) -> int:
            """Read one company's metric JSON and bulk-load into Snowflake."""
            payload = json.loads(Path(extracted_path).read_text(encoding="utf-8"))
            metrics = [ESRSMetric.model_validate(item) for item in payload]
            hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
            with hook.get_conn() as conn:
                inserted = load_metrics(metrics, conn=conn)
            logger.info("load.success", path=extracted_path, rows=inserted)
            return inserted

        load_one.expand(extracted_path=extracted_paths)

    # ── Wire the groups ───────────────────────────────────────────────
    pdfs = ingest_group()
    metric_paths = extract_group(pdfs)
    load_group(metric_paths)


# Instantiate the DAG (TaskFlow API requires the call at module level).
csrd_lake_dag()


# ──────────────────────────────────────────────────────────────────────
# Helpers — kept thin; real logic lives in `csrd_lake.*` modules.
# ──────────────────────────────────────────────────────────────────────


def _read_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pdfplumber.

    Kept here (not in `csrd_lake.ingestion`) because PDF parsing is a DAG-side
    concern — the pure modules treat `pdf_text: str` as the input boundary.
    """
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(f"[page {page.page_number}]\n{text}")
    return "\n\n".join(parts)


def _scrape_latest_report_url(ir_page_url: str) -> str:
    """Discover the latest sustainability PDF link on a company's IR page.

    Stub for v1 — the manifest's `known_report_url` is used directly when
    available, which is the case for all 10 starter CAC 40 entries. v2 will
    implement BeautifulSoup-based scraping with selector fallbacks per IR
    page template.
    """
    raise NotImplementedError(
        f"IR-page scraping not yet implemented for {ir_page_url}. "
        f"Set known_report_url in the manifest for v1."
    )
