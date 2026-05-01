# Changelog

All notable changes to CSRD-Lake. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.1

- 800-datapoint hand-verified gold set with per-language + per-topic accuracy breakdown
- 90-second narrated Loom walkthrough showing live Snowflake schema, dbt lineage graph, and a sample LLM extraction
- DAX 40 + IBEX 35 manifest extension
- IR-page scraping for companies without a known direct PDF URL
- Dashboard v1.1: switch `lib/data.ts` synthetic accessors for live Snowflake reads from `mart_disclosure_published`

## [0.2.0] — 2026-05-01

Weekend 2 build, real deploy, and end-to-end LLM verification path.

### Added

- **dbt project** (`dbt_project/`) — staging (view, dedupes on natural key) + marts (dim_company, dim_metric, dim_period, fact_disclosure, mart_disclosure_published, mart_disclosure_review_queue) + 3 custom data tests + seeded dimensions + dbt-docs-ready schema YAML.
- **Custom dbt data tests** — `metric_value_in_source_text` (catches LLM hallucinations), `confidence_score_in_unit_interval`, `published_and_review_queue_disjoint` (routing invariant).
- **Next.js 16 dashboard** (`dashboard/`) — Server Components, Tailwind v4 design tokens, shadcn-style local primitives (Card / Table / Badge), confidence-routing badges. Three pages: `/`, `/company/[ticker]`, `/portfolio`. All pre-rendered via `generateStaticParams` + `generateMetadata`.
- **43 dashboard structural tests** (`tests/test_dashboard_structure.py`) — file presence, design-token discipline (regex bans 30+ raw color class patterns), no `bg-gradient-to-*`, no `useEffect` for fetching, no emoji icons, generateStaticParams + generateMetadata enforcement, killed-claim anti-regression.
- **Real-LLM verify CLI** (`src/csrd_lake/extraction/cli.py`) — `python -m csrd_lake.extraction.cli --pdf X.pdf --ticker MC.PA --topic E1` runs the real Claude Sonnet + Mistral fallback against any PDF, prints every ESRSMetric with confidence, source citation, and routing decision (~$0.10 per run).
- **Vercel production deploy** at [csrd-lake.vercel.app](https://csrd-lake.vercel.app) (alias secured).
- **Screenshots** — 4 retina PNGs (1440x900 @2x via Playwright headless chromium) embedded inline in README. Reproducible via `node dashboard/scripts/screenshot.mjs`.
- **Walkthrough GIF** (`dashboard/public/screenshots/csrd-lake-dashboard.gif`) — 14-second navigation through home → company → portfolio, 720px / 10 fps / ~5.5 MB. Generated via Playwright video → ffmpeg-static palette-optimized two-pass encoding.
- **Mermaid architecture diagram + tech-stack mindmap** in README.
- **CHANGELOG, SECURITY, PORTABILITY docs** (`docs/PORTABILITY.md` ships full Snowflake↔Synapse / Airflow↔ADF / Claude↔Azure OpenAI mapping with bank-stack notes).
- **Test count: 158** (was 115 in v0.1.0) at 91.81% coverage.

### Changed

- README replaced ASCII architecture diagram with Mermaid flowchart + added tech-stack mindmap.
- README CI badge now points to live GitHub Actions status (was static shield).
- README "Loom walkthrough" placeholder section replaced with reference to the inline GIF and PNGs.
- Project layout note in README updated for dashboard + 158-test count.
- `dashboard/package.json` added `playwright` and `ffmpeg-static` as devDependencies for the screenshot + GIF pipelines.

### Fixed

- Pydantic v2 `field_validator` did not fire on default-None values; replaced with `model_validator(mode='after')` for the value_numeric/value_text mutual-exclusion check.
- Mistral SDK 2.x import path corrected: `from mistralai.client import Mistral` (was top-level `from mistralai import Mistral` which broke in 2.x).
- Anthropic model identifier corrected: `claude-sonnet-4-6` (was `claude-sonnet-4-7` placeholder guess).

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

[Unreleased]: https://github.com/soneeee22000/csrd-lake/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/soneeee22000/csrd-lake/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/soneeee22000/csrd-lake/releases/tag/v0.1.0
