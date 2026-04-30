"""Corporate sustainability report manifest.

The manifest is a packaged TOML file listing companies, their IR pages, and
(optionally) known direct URLs to their latest sustainability reports.

The Airflow `ingest_pdfs` DAG iterates the manifest, optionally falling back
to scraping the IR page when no `known_report_url` is set.

Manifest schema is enforced by Pydantic; see `CompanyEntry`.
"""

from __future__ import annotations

import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, StringConstraints

# Path to the shipped CAC 40 manifest (10 companies, FR-only for v1)
CAC40_MANIFEST_PATH = Path(str(files("csrd_lake.ingestion") / "data" / "cac40.toml"))


# ── Type aliases for clarity at the schema layer ──────────────────────
TickerStr = Annotated[str, StringConstraints(min_length=2, max_length=10)]
CountryISO2 = Annotated[
    str,
    StringConstraints(min_length=2, max_length=2, pattern="^[A-Z]{2}$"),
]
LanguageCode = Annotated[str, StringConstraints(pattern="^(fr|en)$")]


class CompanyEntry(BaseModel):
    """One company in the manifest.

    `known_report_url` is optional — when missing, the ingestion DAG scrapes
    the `ir_page_url` for the latest sustainability PDF.
    """

    ticker: TickerStr
    name: str = Field(min_length=2, max_length=100)
    sector: str = Field(min_length=2, max_length=50)
    country: CountryISO2
    ir_page_url: HttpUrl
    known_report_url: HttpUrl | None = None
    language: LanguageCode


class Manifest(BaseModel):
    """Top-level manifest model — wraps a list of companies."""

    companies: list[CompanyEntry] = Field(min_length=1, max_length=200)


def load_manifest(path: Path) -> Manifest:
    """Load and validate a TOML manifest from disk.

    Args:
        path: Path to a TOML file with a `[[companies]]` array of tables.

    Returns:
        A validated `Manifest`.

    Raises:
        FileNotFoundError: Path does not exist.
        ValueError: TOML parse error.
        pydantic.ValidationError: Schema validation failed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    try:
        with path.open("rb") as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Failed to parse manifest TOML at {path}: {exc}") from exc

    return Manifest.model_validate(raw)
