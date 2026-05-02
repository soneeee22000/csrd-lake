# Changelog

All notable changes to CSRD-Lake. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.1

- 800-datapoint hand-verified gold set with per-language + per-topic accuracy breakdown
- 90-second narrated Loom walkthrough showing live warehouse schema, dbt lineage graph, and a sample LLM extraction
- DAX 40 + IBEX 35 manifest extension
- IR-page scraping for companies without a known direct PDF URL
- Tighten extraction prompt to keep value strings byte-identical to source — currently 14 fact rows fail the `metric_value_in_source_text` test where the LLM normalises "129 million" → 129000000

## [0.4.0] — 2026-05-02

End-to-end validation. Snowflake target promoted from "documented portable" to "verified". Dashboard reorganised landing-first.

### Added

- **Snowflake validation, end-to-end** — bootstrap script (`scripts/bootstrap_snowflake.py`) connects via key-pair auth, runs DDL, loads the 34 already-extracted metrics from `data/extracted/*.json`, runs dbt seed/run/test against the Snowflake target. 34 raw rows → 32 fact rows → 14 published / 18 review on the live `ULWVOTP-MJ06399` account, identical to DuckDB.
- **Key-pair authentication path** — `scripts/generate_snowflake_keypair.py` generates 2048-bit PKCS#8 keys; `csrd_lake.warehouse.loader` and the dbt profile both accept `SNOWFLAKE_PRIVATE_KEY_PATH` (preferred — bypasses MFA enforcement that blocks plain-password auth on free-trial accounts).
- **dbt wrapper** (`scripts/dbt_run.py`) — loads `.env` via `python-dotenv` so `SNOWFLAKE_*` vars reach the dbt subprocess; expands `~` in private-key path; pins `DBT_PROFILES_DIR` to absolute so re-runs from any cwd work.
- **Landing page** at `/` — hero, live warehouse stats (32 metrics / 14 published / 18 review / 7 dbt models), CSRD problem context, six-stage architecture cards, tech stack by layer, honest "real vs stub" callout, CTA. Existing company list moved to `/companies`.
- **Page-citation snippet test surfacing real findings** — the `metric_value_in_source_text` custom dbt test catches 14 LLM string-format issues (e.g. "129 million" → 129000000). 54 of 55 dbt tests pass on Snowflake; the one failure is a working signal, not a regression.

### Fixed

- **CI failing on every push since v0.2.0** — `.gitignore` excluded `uv.lock`, but CI's `astral-sh/setup-uv@v4` cache step required it. Lockfile now tracked (308 KB, applications commit lockfiles).
- **`dashboard/lib/utils.ts` was on disk but never tracked** — the shadcn `cn()` helper would have broken Vercel builds the first time the cache cleared. Now committed.
- **`fact_disclosure` surrogate-key collision** — `disclosure_id` was generated from `(ticker, year, esrs_disclosure, extraction_model)` without `metric_name`, causing TotalEnergies' four E2-4 sub-pollutants to share an ID. Adds `metric_name` to the natural-key tuple.
- **Snowflake DDL** — `CREATE INDEX IF NOT EXISTS` (which Snowflake doesn't support) replaced with `ALTER TABLE … CLUSTER BY`. Bug present since v0.1.0, only surfaced when the DDL was actually run on Snowflake.

## [0.3.0] — 2026-05-02

End-to-end real data — first run of the pipeline against live CAC 40 sustainability reports.

### Added

- **Real PDF ingestion** — three CAC 40 reports downloaded from official IR sites and committed to the manifest as `known_report_url`: LVMH URD 2023 (5.1 MB), TotalEnergies Sustainability & Climate 2024 (10.0 MB), Schneider Electric URD 2024 (14.0 MB — first explicitly CSRD-compliant filing). Total 29.6 MB of real corporate disclosure on disk.
- **Local DuckDB warehouse** (`csrd_lake.warehouse.duckdb_loader`) — drop-in replacement for the Snowflake loader, parameterised on the same `metric_to_row` shape with `?` placeholders. Bootstraps `raw / staging / marts` schemas in `data/warehouse/csrd_lake.duckdb`. PRD §10 Decision-Log fallback now the default for local dev.
- **dbt-duckdb adapter wired** — new `duckdb` target in `dbt_project/profiles.yml`; `_sources.yml` switches database/schema via `target.type` Jinja conditional so the same models compile against either warehouse. `dbt seed && dbt run` materialises 7 models against DuckDB in <1 s.
- **Batch extraction CLI** (`csrd_lake.extraction.batch`) — runs the full 3-PDF × 5-topic matrix, streams results into DuckDB after each topic so a mid-batch crash never loses work, persists per-company JSON archives to `data/extracted/`, prints a routing summary at the end. Cost ~$1.50 wall-clock, ~7 minutes.
- **Topic-keyword page filter** — pre-filters each PDF down to topic-relevant pages (~80 K chars / ~20 K tokens) so prompts fit Anthropic's 30 K-tokens-per-minute free-tier limit. Cuts prompts ~10× without losing recall on the metrics the catalog targets.
- **Rate-limit + Mistral SDK error handling** — the Claude→Mistral fallback chain now catches `anthropic.APIError` (429s, 5xx) and Mistral's broader exception surface so neither provider rate-limiting can crash the batch.
- **Test count: 167** (was 158) — added regression test for dotted-suffix disclosure-code normalisation, full DuckDB loader round-trip suite (6 tests), and `dbt_packages/` exclusion in the project-structure scanner.

### Changed

- `esrs_disclosure` codes are normalised at the LLM-output boundary — sub-codes such as `E1-6.scope_2_location` are stripped to canonical `E1-6` so the fact→dim_metric join resolves cleanly. The dotted form was a prompt-design mistake the schema's 20-character cap accidentally caught; both prompt and validator now agree on canonical codes.
- `pyproject.toml` adds `duckdb>=1.1.0` to base dependencies and `dbt-duckdb>=1.9.0` to the `dbt` extra.
- `data/raw/`, `data/extracted/`, `data/warehouse/` added to `.gitignore`; only `data/samples/` is committed.

### Verified extractions (top published mart by confidence)

- TotalEnergies — net-zero target year 2050 (p.15, 0.99)
- LVMH — 213,268 employees (p.13, 0.95)
- Schneider Electric — net-zero target year 2050 (p.9, 0.95)
- TotalEnergies — 2 work-related fatalities (p.62, 0.90)
- TotalEnergies — 76 Mm³ water consumption (p.105, 0.90)

### Known issue

- 13 of 34 raw rows do not yet appear in `marts.fact_disclosure` — `metric_name` string drift between LLM output and `dim_metric` seed (e.g. `"Total employees"` vs `"Total employees (headcount)"`). Tracked for v0.4.

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
