"""Structural tests for the dbt project.

Verifies the dbt_project/ directory has the expected shape, that all YAML
files parse, that all SQL files are non-empty, and that the seed CSVs are
consistent. Does NOT require dbt to be installed in the dev environment;
real `dbt parse` runs in a separate CI job that installs `--extra dbt`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

DBT_ROOT = Path(__file__).resolve().parents[1] / "dbt_project"

# Vendored dbt packages and dbt build artifacts contain SQL/YAML that this
# project does not own. Exclude them from structural assertions.
_EXCLUDED_DIRS = ("dbt_packages", "target", "logs")


def _is_owned(path: Path) -> bool:
    parts = path.relative_to(DBT_ROOT).parts
    return not any(p in _EXCLUDED_DIRS for p in parts)


# ── File presence ─────────────────────────────────────────────────────


def test_dbt_project_yml_exists() -> None:
    assert (DBT_ROOT / "dbt_project.yml").exists()


def test_profiles_yml_exists() -> None:
    """profiles.yml is committed (it uses env_var, no secrets)."""
    assert (DBT_ROOT / "profiles.yml").exists()


def test_packages_yml_exists() -> None:
    assert (DBT_ROOT / "packages.yml").exists()


def test_required_directories_exist() -> None:
    for sub in ("models/staging", "models/marts", "seeds", "tests"):
        assert (DBT_ROOT / sub).exists(), f"Missing dbt subdir: {sub}"


# ── YAML validity ─────────────────────────────────────────────────────


def _yaml_files() -> list[Path]:
    return sorted(p for p in DBT_ROOT.rglob("*.yml") if _is_owned(p))


@pytest.mark.parametrize(
    "yaml_path",
    _yaml_files(),
    ids=lambda p: str(p.relative_to(DBT_ROOT)),
)
def test_yaml_files_parse(yaml_path: Path) -> None:
    """Every YAML file under dbt_project/ must parse cleanly."""
    yaml.safe_load(yaml_path.read_text(encoding="utf-8"))


def test_dbt_project_yml_has_expected_top_level_keys() -> None:
    config = yaml.safe_load((DBT_ROOT / "dbt_project.yml").read_text(encoding="utf-8"))
    expected_keys = {"name", "version", "profile", "model-paths", "seeds", "vars"}
    assert expected_keys <= set(config.keys()), (
        f"dbt_project.yml missing keys: {expected_keys - set(config.keys())}"
    )


def test_dbt_project_name_is_csrd_lake() -> None:
    config = yaml.safe_load((DBT_ROOT / "dbt_project.yml").read_text(encoding="utf-8"))
    assert config["name"] == "csrd_lake"


def test_confidence_threshold_var_matches_python() -> None:
    """The dbt var `confidence_threshold` must match the Python default."""
    config = yaml.safe_load((DBT_ROOT / "dbt_project.yml").read_text(encoding="utf-8"))
    assert config["vars"]["confidence_threshold"] == 0.80


# ── SQL files non-empty ───────────────────────────────────────────────


def _sql_files() -> list[Path]:
    return sorted(p for p in DBT_ROOT.rglob("*.sql") if _is_owned(p))


@pytest.mark.parametrize(
    "sql_path",
    _sql_files(),
    ids=lambda p: str(p.relative_to(DBT_ROOT)),
)
def test_sql_file_non_empty(sql_path: Path) -> None:
    """Every .sql file under dbt_project/ has actual SQL content."""
    content = sql_path.read_text(encoding="utf-8").strip()
    assert content, f"Empty SQL file: {sql_path}"
    # Must contain at least one of: select / with / config — sanity check.
    lower = content.lower()
    assert any(kw in lower for kw in ("select", "with ", "{{ config")), (
        f"SQL file looks malformed (no select/with/config): {sql_path}"
    )


# ── Seed consistency ──────────────────────────────────────────────────


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_companies_seed_has_ten_rows() -> None:
    """Mirrors the TOML manifest in csrd_lake.ingestion.data.cac40.toml."""
    rows = _read_csv(DBT_ROOT / "seeds" / "companies_seed.csv")
    assert len(rows) == 10


def test_companies_seed_columns_match_manifest_schema() -> None:
    rows = _read_csv(DBT_ROOT / "seeds" / "companies_seed.csv")
    expected_cols = {"ticker", "name", "sector", "country", "ir_page_url", "language"}
    assert set(rows[0].keys()) == expected_cols


def test_companies_seed_languages_valid() -> None:
    rows = _read_csv(DBT_ROOT / "seeds" / "companies_seed.csv")
    for row in rows:
        assert row["language"] in {"fr", "en"}, (
            f"Invalid language in seed: {row['ticker']}={row['language']}"
        )


def test_esrs_metrics_seed_has_19_rows() -> None:
    """Matches the v1 catalog in `csrd_lake.extraction.prompts.ESRS_METRIC_CATALOG`."""
    rows = _read_csv(DBT_ROOT / "seeds" / "esrs_metrics_seed.csv")
    assert len(rows) == 19


def test_esrs_metrics_seed_topics_valid() -> None:
    rows = _read_csv(DBT_ROOT / "seeds" / "esrs_metrics_seed.csv")
    valid_topics = {"E1", "E2", "E3", "S1", "G1"}
    for row in rows:
        assert row["esrs_topic"] in valid_topics, (
            f"Invalid ESRS topic: {row['esrs_topic']} for {row['metric_name']}"
        )


def test_periods_seed_has_one_row_for_fy2024() -> None:
    rows = _read_csv(DBT_ROOT / "seeds" / "periods_seed.csv")
    assert len(rows) == 1
    assert rows[0]["fiscal_year"] == "2024"


# ── Anti-regression: forbidden patterns in dbt SQL ────────────────────


def test_no_killed_claims_in_sql() -> None:
    """The 'replaces MSCI subscription' framing must not appear in dbt comments."""
    forbidden_phrases = [
        "replaces MSCI",
        "replaces a €40",
        "MSCI subscription",
        "Sustainalytics subscription",
    ]
    for sql_path in _sql_files():
        content = sql_path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            assert phrase.lower() not in content.lower(), (
                f"Killed claim '{phrase}' found in {sql_path.name}"
            )


def test_models_reference_correct_sources() -> None:
    """Staging models must read from the `raw` source defined in _sources.yml."""
    stg_disclosure = (DBT_ROOT / "models" / "staging" / "stg_disclosure.sql").read_text()
    assert "{{ source('raw', 'disclosure_extracted') }}" in stg_disclosure


def test_marts_use_ref_not_source() -> None:
    """Marts must read from staging via {{ ref(...) }}, never raw sources directly."""
    for mart in (DBT_ROOT / "models" / "marts").glob("*.sql"):
        content = mart.read_text(encoding="utf-8")
        assert "{{ source(" not in content, (
            f"{mart.name} reads from a source — should ref('stg_*') instead"
        )
