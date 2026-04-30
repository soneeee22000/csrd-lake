# Changelog

All notable changes to CSRD-Lake. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.1

- Next.js 16 dashboard (`/company/[ticker]` + `/portfolio` rollup)
- 800-datapoint hand-verified gold set with per-language + per-topic accuracy breakdown
- 90-second Loom walkthrough linked from README
- DAX 40 + IBEX 35 manifest extension

## [0.1.0] — 2026-04-30 → 2026-05-01

Initial scaffold and Weekend 1 build.

### Added

- **Project structure** with PRD-driven scope and quality gates (`docs/PRD.md`).
- **Pydantic v2 ESRS schemas** (`src/csrd_lake/extraction/schemas.py`) — typed metrics with mandatory `confidence_score` and `source_citation`.
- **Confidence scoring** (`src/csrd_lake/extraction/confidence.py`) — pure deterministic function mapping `(logprob, structural_pass, snippet_match, language_match) → [0, 1]` with a `0.80` routing threshold.
- **PDF ingestion** — TOML-backed manifest of 10 CAC 40 companies (`src/csrd_lake/ingestion/data/cac40.toml`) + httpx + tenacity downloader (`src/csrd_lake/ingestion/downloader.py`) with idempotency, atomic writes, and PDF magic-byte validation.
- **LLM extraction** (`src/csrd_lake/extraction/llm.py`) — Claude Sonnet 4.6 primary via tool-use API, Mistral Large fallback on Anthropic errors or Pydantic validation failures.
- **ESRS metric catalog** (`src/csrd_lake/extraction/prompts.py`) — 19 metrics across 5 ESRS topics (E1, E2, E3, S1, G1) for v1.
- **Snowflake star schema DDL** (`src/csrd_lake/warehouse/ddl.sql`) — `dim_company`, `dim_metric`, `dim_period`, `fact_disclosure`, plus `RAW.DISCLOSURE_EXTRACTED` landing table.
- **Snowflake bulk loader** (`src/csrd_lake/warehouse/loader.py`) — parameterized `executemany` with cursor cleanup and rowcount fallback.
- **Airflow DAG** (`airflow/dags/csrd_lake.py`) — single TaskFlow API DAG with three task groups (ingest / extract / load) and dynamic task mapping (`.expand()`) per company.
- **dbt project** (`dbt_project/`) — staging (view, dedupes on natural key) + marts (dim/fact/published/review_queue) + 3 custom data tests + seeded dimensions.
- **CI** (`.github/workflows/ci.yml`) — ruff + mypy strict + pytest + dbt parse.
- **115 tests** at 91.81% coverage.

### Decided

- Cost-displacement framing (`replaces €40-80k MSCI subscription`) **killed by `/moat-check`** on 2026-04-30 — Briink ships exact PDF→ESRS extraction at €195/month and MSCI's value isn't PDF parsing. Anti-regression tests in `tests/test_dag_structure.py` and `tests/test_dbt_project_structure.py` enforce the absence of the killed phrasing across DAG and dbt SQL.
- Approved framing: **"reference implementation of the Capgemini Sustainability Data Hub / PwC ESG Reporting Manager pattern"**.
- Scope cuts (per PRD §8): FR + EN only; CAC 40 only (DAX 40 stretch); single ESRS framework (no TCFD/ISSB/Pillar 3 cross-walk in v1).

### Known gaps (intentionally deferred)

- Hand-verified gold-set accuracy measurement (planned for v1.1).
- Next.js dashboard (planned for v1.1).
- IR-page scraping for companies without a known direct PDF URL (planned for v1.1; v1 uses the manifest's `known_report_url` only).
- DE / ES extraction (out of scope for v1).

[Unreleased]: https://github.com/soneeee22000/csrd-lake/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/soneeee22000/csrd-lake/releases/tag/v0.1.0
