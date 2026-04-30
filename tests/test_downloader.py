"""Tests for the PDF downloader.

Uses httpx.MockTransport — no network calls. Verifies:
- Successful download writes the body to disk
- PDF magic-byte validation rejects non-PDF responses
- Transient 5xx errors are retried (tenacity)
- Permanent 4xx errors fail fast (no retry)
- Idempotency: existing files with non-zero size are not re-downloaded
- Atomic writes: a failure mid-write does not leave a partial file at the target path
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from csrd_lake.ingestion.downloader import (
    DownloadError,
    NotAPDFError,
    download_pdf,
)

# Minimum valid PDF body for tests — real %PDF magic prefix + filler.
VALID_PDF_BODY = b"%PDF-1.7\n% test fixture\n%%EOF\n"


def _mock_transport(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    """Tiny helper: build a MockTransport from a single handler function."""
    return httpx.MockTransport(handler)


class TestDownloadPdfHappyPath:
    def test_downloads_and_writes_pdf(self, tmp_path: Path) -> None:
        target = tmp_path / "lvmh-2024.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://example.com/report.pdf"
            return httpx.Response(
                200,
                content=VALID_PDF_BODY,
                headers={"content-type": "application/pdf"},
            )

        with httpx.Client(transport=_mock_transport(handler)) as client:
            written_path = download_pdf(
                "https://example.com/report.pdf",
                target,
                client=client,
            )

        assert written_path == target
        assert target.read_bytes() == VALID_PDF_BODY

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Target path's parent directories are created if missing."""
        target = tmp_path / "nested" / "deep" / "report.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=VALID_PDF_BODY)

        with httpx.Client(transport=_mock_transport(handler)) as client:
            download_pdf("https://x/r.pdf", target, client=client)

        assert target.exists()


class TestDownloadPdfIdempotency:
    def test_skips_existing_nonempty_file(self, tmp_path: Path) -> None:
        """If file exists with non-zero size, do not re-download (idempotent ingestion)."""
        target = tmp_path / "report.pdf"
        target.write_bytes(VALID_PDF_BODY)
        original_mtime = target.stat().st_mtime

        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(200, content=VALID_PDF_BODY)

        with httpx.Client(transport=_mock_transport(handler)) as client:
            download_pdf("https://x/r.pdf", target, client=client)

        assert request_count == 0, "Should not have made any HTTP request"
        assert target.stat().st_mtime == original_mtime, "File should be untouched"

    def test_redownloads_zero_byte_file(self, tmp_path: Path) -> None:
        """Existing zero-byte file is treated as a failed prior attempt and re-fetched."""
        target = tmp_path / "report.pdf"
        target.write_bytes(b"")  # zero-byte sentinel of a failed prior write

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=VALID_PDF_BODY)

        with httpx.Client(transport=_mock_transport(handler)) as client:
            download_pdf("https://x/r.pdf", target, client=client)

        assert target.read_bytes() == VALID_PDF_BODY

    def test_force_re_download_overrides_idempotency(self, tmp_path: Path) -> None:
        """`force=True` re-fetches even if file already exists."""
        target = tmp_path / "report.pdf"
        target.write_bytes(b"OLD CONTENT (also not a real PDF, deliberately)")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=VALID_PDF_BODY)

        with httpx.Client(transport=_mock_transport(handler)) as client:
            download_pdf("https://x/r.pdf", target, client=client, force=True)

        assert target.read_bytes() == VALID_PDF_BODY


class TestDownloadPdfValidation:
    def test_rejects_non_pdf_body(self, tmp_path: Path) -> None:
        """A 200 with HTML / non-PDF body raises NotAPDFError, no file written."""
        target = tmp_path / "report.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"<html><body>Not a PDF, sorry</body></html>",
                headers={"content-type": "text/html"},
            )

        with (
            httpx.Client(transport=_mock_transport(handler)) as client,
            pytest.raises(NotAPDFError),
        ):
            download_pdf("https://x/r.pdf", target, client=client)

        assert not target.exists(), "Target must not be written on validation failure"


class TestDownloadPdfRetries:
    def test_retries_transient_5xx(self, tmp_path: Path) -> None:
        """503 → 503 → 200 sequence: succeed after retries."""
        target = tmp_path / "report.pdf"
        attempts = [503, 503, 200]
        idx = {"i": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            status = attempts[idx["i"]]
            idx["i"] += 1
            if status == 200:
                return httpx.Response(200, content=VALID_PDF_BODY)
            return httpx.Response(status, content=b"transient")

        with httpx.Client(transport=_mock_transport(handler)) as client:
            download_pdf("https://x/r.pdf", target, client=client, max_attempts=3)

        assert idx["i"] == 3
        assert target.read_bytes() == VALID_PDF_BODY

    def test_raises_after_exhausting_retries(self, tmp_path: Path) -> None:
        """All 503s for max_attempts → DownloadError raised."""
        target = tmp_path / "report.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, content=b"persistent failure")

        with (
            httpx.Client(transport=_mock_transport(handler)) as client,
            pytest.raises(DownloadError),
        ):
            download_pdf("https://x/r.pdf", target, client=client, max_attempts=2)

        assert not target.exists()

    def test_does_not_retry_404(self, tmp_path: Path) -> None:
        """Permanent 4xx errors fail fast — no point retrying."""
        target = tmp_path / "report.pdf"
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(404, content=b"not found")

        with (
            httpx.Client(transport=_mock_transport(handler)) as client,
            pytest.raises(DownloadError),
        ):
            download_pdf("https://x/r.pdf", target, client=client, max_attempts=3)

        assert request_count == 1, "Should not retry on 404"


class TestDownloadPdfAtomicWrite:
    def test_no_partial_file_left_when_validation_fails(self, tmp_path: Path) -> None:
        """If the response body fails magic-byte validation, target path stays clean."""
        target = tmp_path / "report.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"NOT-A-PDF")

        with (
            httpx.Client(transport=_mock_transport(handler)) as client,
            pytest.raises(NotAPDFError),
        ):
            download_pdf("https://x/r.pdf", target, client=client)

        # The whole point of atomicity: no .partial / .tmp / .pdf at the target path
        assert not target.exists()
        assert list(target.parent.iterdir()) == [], (
            "No leftover partial files in the target directory"
        )
