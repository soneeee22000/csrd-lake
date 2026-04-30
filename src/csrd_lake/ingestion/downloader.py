"""PDF downloader with retry, idempotency, and PDF magic-byte validation.

Used by the Airflow `ingest_pdfs` DAG to fetch corporate sustainability PDFs.
Pure sync function — Airflow tasks are sync by default.

Behaviors:
- Retries on 5xx with exponential backoff (tenacity).
- Fails fast on 4xx (no point retrying a 404 or 403).
- Validates PDF magic bytes (`%PDF`) before writing to disk.
- Atomic write: download to `<target>.partial`, rename on success.
- Idempotent: skips download if target exists with size > 0 (unless `force=True`).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# PDFs always start with the bytes `%PDF` (PDF 1.0+ specification).
PDF_MAGIC = b"%PDF"


class DownloadError(Exception):
    """Raised when a PDF could not be downloaded after all retries."""


class NotAPDFError(DownloadError):
    """Raised when the downloaded body is not a valid PDF (magic bytes missing)."""


class _TransientHTTPError(Exception):
    """Internal marker used by tenacity to know which errors to retry."""


def download_pdf(
    url: str,
    target: Path,
    *,
    client: httpx.Client | None = None,
    max_attempts: int = 3,
    timeout_seconds: float = 30.0,
    force: bool = False,
) -> Path:
    """Download a PDF from `url` to `target`.

    Args:
        url: Direct PDF URL to fetch.
        target: Filesystem path where the PDF should land.
        client: Optional httpx.Client (for testing with MockTransport).
            If None, a fresh client is created per call.
        max_attempts: Total attempts (including the first). Retries apply only to 5xx.
        timeout_seconds: Per-request timeout.
        force: If True, re-download even if target already exists.

    Returns:
        The path the PDF was written to (same as `target`).

    Raises:
        DownloadError: All retries exhausted, or permanent HTTP error.
        NotAPDFError: Response body is not a valid PDF.
    """
    # ── Idempotency check ────────────────────────────────────────────
    if not force and target.exists() and target.stat().st_size > 0:
        logger.info("ingestion.skip", url=url, target=str(target), reason="exists")
        return target

    # If a zero-byte sentinel exists from a prior failure, remove it before retrying.
    if target.exists() and target.stat().st_size == 0:
        target.unlink()

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")

    # ── Build the inner fetcher with tenacity wrapping ───────────────
    @retry(
        retry=retry_if_exception_type(_TransientHTTPError),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=2.0),
        reraise=False,
    )
    def _fetch() -> bytes:
        owns_client = client is None
        c = client if client is not None else httpx.Client(timeout=timeout_seconds)
        try:
            response = c.get(url, follow_redirects=True)
        finally:
            if owns_client:
                c.close()

        if 500 <= response.status_code < 600:
            logger.warning(
                "ingestion.transient",
                url=url,
                status=response.status_code,
            )
            raise _TransientHTTPError(f"HTTP {response.status_code}")

        if response.status_code >= 400:
            # Permanent failure — re-raise as DownloadError, do NOT retry.
            raise DownloadError(f"HTTP {response.status_code} for {url}")

        return response.content

    # ── Execute, translating tenacity outcomes into our error types ──
    try:
        body = _fetch()
    except RetryError as exc:
        # All retries exhausted on transient errors.
        raise DownloadError(f"Exhausted {max_attempts} attempts fetching {url}") from exc

    if not body.startswith(PDF_MAGIC):
        raise NotAPDFError(f"Response body for {url} is not a PDF (got {body[:8]!r}…)")

    # ── Atomic write: temp + rename ──────────────────────────────────
    partial.write_bytes(body)
    partial.replace(target)
    logger.info(
        "ingestion.success",
        url=url,
        target=str(target),
        bytes=len(body),
    )
    return target
