# Understanding CSRD-Lake

A plain-language guide to what this project is, why it exists, how it
fits together, and what's real versus aspirational. Read this before
the source if you're new to the repo, or before a CV / interview
conversation if you built it.

## 1. The business problem (the "why")

In 2024 the EU passed **CSRD** — the Corporate Sustainability Reporting
Directive. Starting with **wave 1 = FY2024 reports**, every large EU
public company has to publish detailed sustainability disclosures
using a standard called **ESRS** (European Sustainability Reporting
Standards) — over 1,100 datapoints across climate, pollution, water,
workforce, and governance.

The reports come out as **300–700 page PDFs**. Investors, banks,
regulators, and corporate compliance teams all need this data
**structured and queryable**, not as PDFs.

This is exactly the problem the Big-4 ESG and consulting practices
(Deloitte, PwC, KPMG, EY) and integrators like Capgemini are selling
solutions for to French G-SIBs (BNP Paribas, Société Générale, Crédit
Agricole, BPCE) right now:

- Capgemini calls theirs **"Sustainability Data Hub"**
- PwC calls theirs **"ESG Reporting Manager"**
- The pattern: ingest sustainability PDFs → extract structured ESRS
  metrics → land in a cloud warehouse → expose via dashboard / API
  for downstream reporting and analysis.

**CSRD-Lake is a reference implementation of that pattern.** Not the
product — the _blueprint_. The killed framing "replaces a €40-80k MSCI
subscription" was demonstrably wrong (per `/moat-check 2026-04-30`)
because the production vendors (Credo AI, Holistic AI, OneTrust,
Saidot, Naaia) have far more functionality than a portfolio piece
could. The honest framing is **"the architectural skeleton a Big-4
sustainability practice would build for a banking client"**.

## 2. What this project does, in one sentence

> Take real CAC 40 sustainability PDFs (LVMH, TotalEnergies, Schneider
> Electric), use Claude + Mistral to extract ESRS metrics with
> page-level source citations and confidence scores, land them in a
> Snowflake star-schema warehouse (with a DuckDB local-dev fallback)
> modelled with dbt, and surface them on a Next.js dashboard deployed
> to Vercel.

Every word in that sentence maps to a Cloud Data Engineer skill. We
come back to that in §5.

## 3. The architecture, layer by layer

```
PDFs → Python ingestion → LLM extraction → Snowflake / DuckDB warehouse → dbt models → JSON snapshot → Next.js dashboard
```

| Layer                                        | What it does                                                                                                                                                                                                                                                                                                       | Real example                                                                                |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| **Ingestion** (`src/csrd_lake/ingestion/`)   | Reads a TOML manifest of CAC 40 companies, downloads each company's sustainability PDF from their IR site with retries + atomic writes + magic-byte validation                                                                                                                                                     | `data/raw/SU.PA-2024.pdf` — 14 MB, 676 pages, Schneider Electric's first CSRD-compliant URD |
| **Extraction** (`src/csrd_lake/extraction/`) | For each PDF × ESRS topic (E1 climate / E2 pollution / E3 water / S1 workforce / G1 governance), filters to topic-relevant pages, sends to Claude Sonnet, falls back to Mistral Large on rate-limit or malformed output, returns Pydantic-validated `ESRSMetric` objects with confidence scores and page citations | "TotalEnergies SO2 = 12 kt, page 105, confidence 0.93 → routes to published mart"           |
| **Warehouse** (`src/csrd_lake/warehouse/`)   | Bulk-inserts validated metrics into `raw.disclosure_extracted`. Two interchangeable backends: **DuckDB** (local, zero-signup) or **Snowflake** (production target) — same column shape, same dbt models, just different placeholders (`?` vs `%s`)                                                                 | `data/warehouse/csrd_lake.duckdb` — 34 raw rows                                             |
| **Transformation** (`dbt_project/`)          | dbt-modeled star schema: `stg_disclosure` (cleaning + dedup) → `dim_company` / `dim_metric` (auto-extending) / `dim_period` → `fact_disclosure` → `mart_disclosure_published` (conf ≥ 0.80) and `mart_disclosure_review_queue` (conf < 0.80)                                                                       | 14 published, 18 in human review                                                            |
| **Export** (`scripts/`)                      | Queries the marts and writes a JSON snapshot the dashboard imports at build time — Vercel can't query DuckDB at runtime                                                                                                                                                                                            | `dashboard/lib/data/disclosures.json` — 32 real metrics                                     |
| **Dashboard** (`dashboard/`)                 | Next.js 16 + Tailwind v4 + shadcn primitives, statically prerendered to Vercel. Three pages: home (10 companies), per-company ESG profile, portfolio rollup                                                                                                                                                        | csrd-lake.vercel.app                                                                        |
| **Orchestration** (`airflow/dags/`)          | Airflow 2.10 DAG that composes ingest → extract → load with TaskFlow API and dynamic task mapping. Defined for orchestration-pattern visibility; the local batch CLI is the dev-loop entry point                                                                                                                   | `airflow/dags/csrd_lake.py`                                                                 |

Three cross-cutting principles to be able to defend:

1. **Every metric carries its source citation** — `(page_number,
verbatim_snippet)`. A custom dbt test asserts the snippet contains
   the value. This is how the warehouse survives an ESG audit.
2. **Confidence scoring routes uncertain extractions to a human
   review queue** — never silently publishes. Confidence factors:
   LLM logprob, Pydantic structural pass, snippet contains value,
   language match.
3. **Two LLMs, one fallback chain** — Claude Sonnet primary, Mistral
   Large fallback. Catches model errors, rate limits, malformed JSON.

## 4. Honest status — what's real, what's stub

|                    | Real / done                                                                                                                                                                     | Stub / aspirational                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **PDF ingestion**  | 3 CAC 40 reports downloaded from real IR sites                                                                                                                                  | Only 3 of 10 manifest entries; IR-page scraping not implemented                              |
| **LLM extraction** | 34 real metrics extracted, real Claude + Mistral API calls, ~$1.50 spent                                                                                                        | The "96% accuracy" claim is **pending hand-verified gold set** — do not quote until verified |
| **Warehouse**      | DuckDB local AND Snowflake (validated end-to-end with key-pair auth, 34 rows loaded, 7 dbt models built)                                                                        | —                                                                                            |
| **dbt**            | 7 models + 54 generic data tests + 3 custom tests, green against DuckDB; 54 of 55 tests green against Snowflake (one custom test correctly catches 14 LLM string-format issues) | —                                                                                            |
| **Airflow**        | DAG file exists, parses, has retry policy + dynamic task mapping                                                                                                                | Not actually run — extraction goes through a plain Python CLI                                |
| **Dashboard**      | Live at csrd-lake.vercel.app, landing page + real ESRS data after v0.4.0                                                                                                        | Portfolio exposure values are clearly-labelled synthetic (real Scope 1, synthetic loan book) |
| **Tests**          | 168 pytest cases, ~91% coverage on `src/`, structural tests for DAG + dbt + dashboard                                                                                           | —                                                                                            |
| **CI/CD**          | GitHub Actions runs lint + mypy + pytest + dbt parse on every push, no secrets needed                                                                                           | —                                                                                            |

**The gap to "production":** Airflow actually scheduled, hand-verified
gold-set accuracy. Everything else is real, including the Snowflake
warehouse target now validated against a real account.

## 5. What this code demonstrates (skills mapping)

| Skill area                          | Where it shows up                                                                                                           |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Cloud data warehouse + modeling** | dbt star schema, 7 models, 54 dbt tests, custom data tests for source-snippet integrity, auto-extending `dim_metric`        |
| **Python (typed, tested)**          | Python 3.12 + Pydantic v2 at LLM boundary, 167 pytest cases at ~91% coverage, strict mypy, ruff format-check in CI          |
| **Cloud orchestration**             | Airflow 2.10 DAG with retries, idempotency, dynamic task mapping (`.expand()`), TaskFlow API                                |
| **AI/GenAI integration**            | Real LLM fallback chain (Claude → Mistral), structured output via tool-use, confidence scoring, source-citation enforcement |
| **Modern data stack fluency**       | uv lockfiles, ruff, strict mypy, GitHub Actions CI, Vercel deploy, dbt-utils, Next.js 16 + Tailwind v4                      |
| **Domain knowledge (ESG / CSRD)**   | ESRS catalog implementation, double-materiality awareness, page-citation audit pattern, confidence routing                  |
| **Engineering rigor**               | PRD-driven build, ADRs, CHANGELOG per release, killed-claim discipline (`/moat-check`), test-first on bug fixes             |

## 6. How to read this repository

If you have 15 minutes:

1. `README.md` — architecture diagram, hero metrics, quickstart
2. `docs/PRD.md` — full product requirements, every feature traces to a user story
3. `src/csrd_lake/extraction/llm.py` — the spine: LLM fallback chain, structured output, confidence scoring
4. `dbt_project/models/marts/dim_metric.sql` — the auto-extending dimension that handles real-world disclosure granularity
5. `tests/test_llm.py` — how the extraction layer is tested (mock SDK clients, no API calls in CI)

If you have 60 minutes:

1. Run `make smoke` — sanity check (no external services needed)
2. Run `make verify-llm PDF=data/samples/lvmh-2024.pdf TICKER=MC.PA TOPIC=E1` — real-LLM single-extraction round-trip (~$0.10)
3. Open `docs/PORTABILITY.md` — the Snowflake↔Synapse / Airflow↔ADF / Claude↔Azure OpenAI mapping, useful if you're evaluating the architecture for an Azure or AWS shop

## 7. CV / interview talking points

If you're considering this project as portfolio evidence for a Cloud
Data Engineer / ESG Engineer / consulting-build role, the honest
framing is:

> _Reference implementation of the Big-4 / Capgemini "Sustainability
> Data Hub" pattern: Python + Airflow + dbt + Snowflake/DuckDB +
> Claude/Mistral GenAI extraction with page-level audit lineage.
> Live dashboard at csrd-lake.vercel.app._

Three CV bullets that pass the "defensible in a 30-minute technical
interview" test:

- _End-to-end ESG data pipeline ingesting real CAC 40 sustainability
  PDFs (LVMH, TotalEnergies, Schneider Electric), extracting ESRS
  metrics via Claude Sonnet with Mistral fallback, validated through
  Pydantic schemas and routed by confidence score (≥0.80 published /
  <0.80 to human review)._
- _dbt star schema (dim_company / dim_metric / dim_period /
  fact_disclosure + 2 reporting marts), with auto-extending
  dimensions that adapt to granular sub-disclosures (e.g.
  TotalEnergies splits E2-4 pollutants into NMVOC/NOx/SO2/PM
  separately)._
- _Designed for portability: same dbt models compile against
  Snowflake (production) or DuckDB (local dev) via a target-type
  Jinja conditional. Airflow 2.10 DAG with TaskFlow API + dynamic
  task mapping orchestrates the ingest → extract → load chain._

**Things to avoid saying:**

- "Production-deployed Snowflake pipeline" — it's not deployed there.
- "96% extraction accuracy" — gold set isn't verified yet.
- "Replaces a €40-80k MSCI subscription" — wrong on multiple counts (`/moat-check 2026-04-30`).
- "I built a Capgemini Sustainability Data Hub competitor" — portfolio piece, not a vendor product.

## 8. What's still open

- **Gold-set hand-verification** to back any accuracy claim
- **`make demo` cold-start <15 min** end-to-end timing (PRD §10 gate)
- **Loom 90-second walkthrough**
- **dbt docs site** deployed
- **Topic-keyword filter ranking** — currently first-match-wins, should rank by keyword density / numeric-token density to keep high-value pages
- **Snowflake free-trial validation run** — prove the same models compile against the production target
