"""Tests for the corporate sustainability report manifest loader.

Manifest is a packaged TOML file (`csrd_lake.ingestion.data.cac40.toml`).
It lists 10 CAC 40 companies with their IR pages and known report URLs.

Tests cover schema validation, uniqueness, URL well-formedness, and the
shipped CAC 40 starter set.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from csrd_lake.ingestion.manifest import (
    CAC40_MANIFEST_PATH,
    CompanyEntry,
    Manifest,
    load_manifest,
)


class TestCompanyEntry:
    """Pydantic model for one company in the manifest."""

    def _valid_payload(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "ticker": "MC.PA",
            "name": "LVMH",
            "sector": "Luxury",
            "country": "FR",
            "ir_page_url": "https://www.lvmh.com/investors/",
            "known_report_url": "https://example.com/lvmh-2024.pdf",
            "language": "fr",
        }
        base.update(overrides)
        return base

    def test_valid_entry_validates(self) -> None:
        entry = CompanyEntry(**self._valid_payload())  # type: ignore[arg-type]
        assert entry.ticker == "MC.PA"
        assert entry.country == "FR"
        assert entry.language == "fr"

    def test_known_report_url_is_optional(self) -> None:
        payload = self._valid_payload()
        del payload["known_report_url"]
        entry = CompanyEntry(**payload)  # type: ignore[arg-type]
        assert entry.known_report_url is None

    def test_invalid_ticker_too_short_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyEntry(**self._valid_payload(ticker="X"))  # type: ignore[arg-type]

    def test_invalid_country_not_iso2_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyEntry(**self._valid_payload(country="France"))  # type: ignore[arg-type]

    def test_invalid_language_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyEntry(**self._valid_payload(language="de"))  # type: ignore[arg-type]

    def test_non_https_ir_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyEntry(**self._valid_payload(ir_page_url="ftp://lvmh.com/"))  # type: ignore[arg-type]


class TestLoadManifest:
    """Load and validate the shipped CAC 40 manifest."""

    def test_cac40_manifest_path_exists(self) -> None:
        """The packaged TOML manifest is on disk and findable."""
        assert CAC40_MANIFEST_PATH.exists()
        assert CAC40_MANIFEST_PATH.suffix == ".toml"

    def test_load_manifest_returns_manifest_object(self) -> None:
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        assert isinstance(manifest, Manifest)

    def test_cac40_has_ten_companies(self) -> None:
        """PRD §7 Weekend 1 target: 30 PDFs across the manifest. Starter set = 10."""
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        assert len(manifest.companies) == 10

    def test_all_tickers_unique(self) -> None:
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        tickers = [c.ticker for c in manifest.companies]
        assert len(set(tickers)) == len(tickers), "Duplicate ticker in manifest"

    def test_all_companies_french(self) -> None:
        """v1 starter set is CAC 40 only. DAX 40 + IBEX 35 stretch deferred."""
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        assert all(c.country == "FR" for c in manifest.companies)

    def test_all_languages_fr_or_en(self) -> None:
        """PRD §8 — DE/ES out of scope for v1."""
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        assert all(c.language in {"fr", "en"} for c in manifest.companies)

    def test_all_ir_urls_https(self) -> None:
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        for company in manifest.companies:
            assert str(company.ir_page_url).startswith("https://"), (
                f"{company.ticker} IR URL must be https"
            )

    def test_load_manifest_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.toml"
        with pytest.raises(FileNotFoundError):
            load_manifest(missing)

    def test_load_manifest_malformed_toml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.toml"
        bad.write_text("this is = not [valid TOML")
        with pytest.raises(ValueError, match="Failed to parse manifest"):
            load_manifest(bad)

    def test_load_manifest_missing_required_field_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "missing.toml"
        bad.write_text(
            '[[companies]]\nticker = "MC.PA"\nname = "LVMH"\n# missing other required fields\n'
        )
        with pytest.raises(ValidationError):
            load_manifest(bad)


class TestManifestExpectedCompanies:
    """Sanity check the actual content of the shipped manifest."""

    def test_includes_known_csrd_strong_reporters(self) -> None:
        """Verify the manifest contains companies known for strong ESRS disclosures."""
        manifest = load_manifest(CAC40_MANIFEST_PATH)
        tickers = {c.ticker for c in manifest.companies}
        # Subset that we know publishes detailed ESRS reports
        expected_subset = {"MC.PA", "TTE.PA", "BNP.PA", "SAN.PA"}
        assert expected_subset.issubset(tickers), (
            f"Missing canonical CAC 40 reporters: {expected_subset - tickers}"
        )
