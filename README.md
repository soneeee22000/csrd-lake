# CSRD-Lake

> **End-to-end CSRD/ESRS data pipeline reference implementation** — Snowflake (validated) + DuckDB local + dbt star schema + Airflow orchestration + Claude/Mistral GenAI extraction with page-level audit lineage.
>
> Same architectural pattern Capgemini's Sustainability Data Hub and PwC's ESG Reporting Manager deploy at French banks today — built solo as an open-source reference implementation.

**Live dashboard:** [csrd-lake.vercel.app](https://csrd-lake.vercel.app) · **Source:** [github.com/soneeee22000/csrd-lake](https://github.com/soneeee22000/csrd-lake) · **Project context:** [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)

![CSRD-Lake dashboard walkthrough — home → per-company ESG profile → portfolio rollup](dashboard/public/screenshots/csrd-lake-dashboard.gif)

[![CI](https://github.com/soneeee22000/csrd-lake/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/soneeee22000/csrd-lake/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![dbt 1.11](https://img.shields.io/badge/dbt-1.11-orange.svg)
![Snowflake validated](https://img.shields.io/badge/snowflake-validated-blue.svg)
![DuckDB local](https://img.shields.io/badge/duckdb-local-fff000.svg)
![Airflow 2.10](https://img.shields.io/badge/airflow-2.10-red.svg)
![Next.js 16](https://img.shields.io/badge/next.js-16-black.svg)
![Tests](https://img.shields.io/badge/tests-168%20passing-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)
![Last commit](https://img.shields.io/github/last-commit/soneeee22000/csrd-lake/main)

---

## Live dashboard

Four pages, all server-rendered, all pre-built at deploy time:

| Page                                                                                                     | Live URL                                                                                                                                                                                     | Screenshot                                                        |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Landing** — CSRD context, live warehouse stats, six-stage architecture, honest "real vs stub" callout  | [csrd-lake.vercel.app](https://csrd-lake.vercel.app)                                                                                                                                         | [home.png](dashboard/public/screenshots/home.png)                 |
| **Companies** — 3 of 10 manifest companies with extracted profiles + pending-ingestion footnote          | [/companies](https://csrd-lake.vercel.app/companies)                                                                                                                                         | —                                                                 |
| **Per-company ESG profile** — metrics grouped by ESRS topic, confidence routing badges, source citations | [/company/MC.PA](https://csrd-lake.vercel.app/company/MC.PA) · [/company/SU.PA](https://csrd-lake.vercel.app/company/SU.PA) · [/company/TTE.PA](https://csrd-lake.vercel.app/company/TTE.PA) | [company-lvmh.png](dashboard/public/screenshots/company-lvmh.png) |
| **Portfolio rollup** — synthetic 10-corporate loan-book over real Scope 1 emissions where extracted      | [/portfolio](https://csrd-lake.vercel.app/portfolio)                                                                                                                                         | [portfolio.png](dashboard/public/screenshots/portfolio.png)       |

![CSRD-Lake home page](dashboard/public/screenshots/home.png)

![Per-company ESG profile (LVMH)](dashboard/public/screenshots/company-lvmh.png)

![Portfolio rollup](dashboard/public/screenshots/portfolio.png)

---

## What this is

CSRD-Lake is a working reference implementation of the data architecture French banks (BNP Paribas, Société Générale, Crédit Agricole, BPCE) and the Big-4 practices supporting them ship for **CSRD wave-1 reporting in 2026**.

It ingests corporate sustainability PDFs from CAC 40 issuers, extracts ESRS metrics from a 19-entry catalog covering 5 topics (E1 climate / E2 pollution / E3 water / S1 workforce / G1 governance) using Claude Sonnet (with Mistral Large as fallback), validates each extraction against Pydantic schemas with confidence scoring, and lands the results in a Snowflake star schema (validated end-to-end) modelled with dbt — a DuckDB local target compiles the same models for laptop development with no cloud signup.

Every extracted metric carries:

- A **confidence score** in `[0.0, 1.0]` — values below `0.80` route automatically to a human-review queue (`mart_disclosure_review_queue`) instead of the published mart.
- A **source citation** — page number + verbatim snippet from the source PDF, enforced as a hard requirement of the extraction schema.
- A **language tag** (`fr` or `en` in v1) verified against the actual PDF content.
- A **model tag** (`claude-sonnet-4-6` or `mistral-large-latest`) for per-model accuracy reporting.

## What this is NOT

- ❌ **Not a product replacing MSCI / Sustainalytics / Bloomberg ESG / Briink / any other ESG data vendor.** Those vendors sell curated ratings, multi-thousand-issuer coverage, and analyst time. CSRD-Lake is a portfolio piece demonstrating the architectural pattern, not a competing product.
- ❌ **Not a real bank loan book.** The `/portfolio` rollup demo uses a clearly-labelled synthetic 10-corporate exposure map composed over real Scope 1 emissions where they have been extracted.
- ❌ **Not a complete CSRD compliance solution.** Single framework only (CSRD/ESRS); no TCFD/ISSB/Pillar 3 cross-walks in v1.
- ❌ **Not production-grade authentication, RBAC, or SOC 2 controls.** Out of scope for a portfolio piece.

## Why this exists

In 2024 the EU passed the **Corporate Sustainability Reporting Directive (CSRD)**. From wave 1 (FY2024 reports) onward, every large EU public company must publish detailed sustainability disclosures using the **European Sustainability Reporting Standards (ESRS)** — over 1,100 datapoints across climate, pollution, water, workforce, and governance. The reports come out as **300–700 page PDFs**. Investors, banks, regulators, and corporate compliance teams need this data **structured and queryable**, not as PDFs.

This is the problem Big-4 ESG practices and integrators (Capgemini, Deloitte, PwC, KPMG, EY) are solving for French G-SIBs (BNP Paribas, Société Générale, Crédit Agricole, BPCE) right now under names like **"Sustainability Data Hub"** (Capgemini), **"ESG Reporting Manager"** (PwC), and **"CSRD 360 Navigator"**. The pattern is consistent: ingest sustainability PDFs → extract structured ESRS metrics → land in a cloud warehouse → expose via dashboard / API for downstream reporting and analysis.

CSRD-Lake is a working reference implementation of that pattern, end-to-end, on real CAC 40 disclosures. **For the full project context** — the regulatory background, layer-by-layer architecture walkthrough, honest "real vs stub" status table, and the skills the codebase demonstrates — see [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

## Architecture

```mermaid
flowchart TD
    A["CAC 40 / DAX 40<br/>IR pages"] -->|"httpx + tenacity<br/>idempotent + atomic"| B["Raw PDFs on disk"]
    B -->|"Airflow ingest_pdfs DAG<br/>mapped per company"| C["Pydantic ESRSMetric<br/>schemas"]
    C -->|"Claude Sonnet 4.6<br/>tool-use API"| D{"Extraction<br/>valid?"}
    D -->|"no"| F["Mistral Large<br/>fallback"]
    D -->|"yes"| E["Per-metric confidence<br/>+ source citation"]
    F --> E
    E -->|"warehouse loader<br/>parameterized executemany"| G[("Snowflake<br/>RAW.DISCLOSURE_EXTRACTED")]
    G -->|"dbt staging view<br/>dedupe on natural key"| H[("staging.stg_disclosure")]
    H -->|"dbt model<br/>joins to dimensions"| I[("marts.fact_disclosure")]
    I -->|"confidence &ge; 0.80"| K[("mart_disclosure_published<br/>dashboard backend")]
    I -->|"confidence &lt; 0.80"| J[("mart_disclosure_review_queue<br/>human review surface")]
    K --> L["Next.js 16 dashboard<br/>csrd-lake.vercel.app"]

    classDef published fill:#d1fae5,stroke:#065f46,color:#000
    classDef review fill:#fef3c7,stroke:#92400e,color:#000
    classDef warehouse fill:#dbeafe,stroke:#1e40af,color:#000
    class K published
    class J review
    class G,H,I warehouse
```

See [`docs/PRD.md`](docs/PRD.md) for full requirements, edge-case handling, and quality gates.

## Hero metrics

> **Every numeric claim below has explicit test conditions** — verify with the linked commands.

| Claim                                                                                                                    | Test condition                                                                                                                                                                                                                                                                                                                             | How to verify                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **168 tests passing at ~91% coverage**                                                                                   | pytest with `--cov-fail-under=70`, branch coverage enabled, full suite                                                                                                                                                                                                                                                                     | `make test`                                                                                                                                                                   |
| **7 layered modules** ingestion / extraction / warehouse / orchestration / dbt staging / dbt marts / dbt reporting marts | One Python package per layer; one Airflow DAG composes them                                                                                                                                                                                                                                                                                | `tree src/csrd_lake airflow dbt_project/models`                                                                                                                               |
| **10 CAC 40 companies in manifest, 3 with extracted profiles, 19 ESRS metrics, 5 ESRS topics** (E1, E2, E3, S1, G1)      | Manifest + catalog mirrored between Python (`prompts.py`) and dbt seeds (`esrs_metrics_seed.csv`); structural test enforces parity                                                                                                                                                                                                         | `pytest tests/test_dbt_project_structure.py -k seed`                                                                                                                          |
| **32 ESRS metrics extracted, 14 published / 18 review-queued**                                                           | Real Claude + Mistral extractions against LVMH URD 2023, TotalEnergies S&C 2024, Schneider Electric URD 2024 (first explicitly CSRD-compliant) — every value carries a page citation                                                                                                                                                       | `python scripts/export_dashboard_data.py --duckdb data/warehouse/csrd_lake.duckdb`                                                                                            |
| **Snowflake currently sources the live dashboard snapshot**                                                              | Bootstrap script runs DDL + loads metrics via key-pair auth (bypasses MFA), dbt builds `RAW_MARTS.*` against `ULWVOTP-MJ06399`. The committed `dashboard/lib/data/disclosures.json` was exported from Snowflake — the JSON's `warehouse` field records the engine that answered the query. DuckDB target produces a byte-identical export. | `python scripts/bootstrap_snowflake.py --truncate && python scripts/dbt_run.py deps seed run test --target dev && python scripts/export_dashboard_data.py --source snowflake` |
| **3 custom dbt data-quality tests**                                                                                      | metric-value-in-source / confidence-in-[0,1] / published-and-review-queue-disjoint                                                                                                                                                                                                                                                         | `dbt test --select test_type:data`                                                                                                                                            |
| **No "vendor displacement" claims anywhere in the repo**                                                                 | `/moat-check` killed the "replaces €40-80k MSCI" framing on 2026-04-30 because Briink ships PDF→ESRS extraction at €195/month and MSCI's value is curated ratings, not parsing. Anti-regression test enforces this.                                                                                                                        | `pytest tests/ -k killed_claims`                                                                                                                                              |
| **Conventional commits, zero AI co-author tags**                                                                         | All commits follow `feat(scope): subject` format; zero "Co-Authored-By: Claude" footers                                                                                                                                                                                                                                                    | `git log --format="%H %s"`                                                                                                                                                    |
| **96% extraction accuracy on a hand-verified gold set**                                                                  | _Pending Weekend 2 hand-verification of 800 datapoints (50 companies × 16 metrics) against published structured ESRS tables._ Number will be updated with the actual measured accuracy + per-language + per-topic breakdown.                                                                                                               | TBD — verification harness in v2                                                                                                                                              |

## Tech stack

| Layer             | Choice                                                                                             | Why                                                                                       |
| ----------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Orchestration     | **Apache Airflow 2.10** (Docker Compose)                                                           | Modern data stack canonical; portable to MWAA / Astronomer / ADF                          |
| Extraction LLM    | **Claude Sonnet 4.6** primary + **Mistral Large** fallback                                         | Claude's tool-use API for structured outputs; Mistral as cost / FR-language fallback      |
| Schema validation | **Pydantic v2**                                                                                    | Type-safe LLM output validation at the boundary                                           |
| Warehouse         | **Snowflake** (live snapshot source, key-pair auth) and **DuckDB** (local-dev target)              | Same dbt models, byte-identical exports — proves warehouse portability under one codebase |
| Transformations   | **dbt-core 1.11** with `dbt-snowflake` + `dbt-duckdb` + `dbt_utils`                                | Lineage + tests + docs; auto-extending `dim_metric` accepts real-world sub-disclosures    |
| Dashboard         | **Next.js 16** + Tailwind v4 (live at csrd-lake.vercel.app)                                        | Server Components, pre-rendered, design-token discipline                                  |
| PDF parsing       | `pdfplumber` + `pypdf`                                                                             | Text extraction from sustainability PDFs                                                  |
| HTTP              | `httpx` + `tenacity`                                                                               | Retry-aware async-ready downloader                                                        |
| Tests             | `pytest` + dbt tests (`not_null`, `unique`, `accepted_values`, `relationships`, custom data tests) | Pyramid + data-quality                                                                    |
| CI                | **GitHub Actions** (lint + mypy + pytest + dbt parse)                                              | Quality gates enforced pre-merge                                                          |

```mermaid
mindmap
  root((CSRD-Lake))
    Orchestration
      Apache Airflow 2.10
      Docker Compose
      TaskFlow API
      Dynamic task mapping
    Extraction
      Claude Sonnet 4.6
      Mistral Large
      Pydantic v2
      Structured outputs
    Ingestion
      httpx + tenacity
      pdfplumber + pypdf
      TOML manifest
      Magic-byte validation
    Warehouse
      Snowflake validated
      DuckDB local
      Star schema
      Parameterized executemany
      RSA key-pair auth
    Transformation
      dbt-core 1.11
      dbt-snowflake
      dbt-duckdb
      dbt_utils
      Auto-extending dim_metric
      Custom data tests
    Dashboard
      Next.js 16
      React 19
      Tailwind v4
      Server Components
      Static prerender
    Quality
      pytest 168 cases
      ruff + mypy strict
      91% coverage
      Anti-regression tests
    CI/CD
      GitHub Actions
      Vercel
      Conventional commits
```

## Quickstart

**Prerequisites:** Python 3.12, [`uv`](https://github.com/astral-sh/uv), Anthropic + Mistral API keys. Snowflake credentials are optional — the local DuckDB target is the default for development.

```bash
# 1. Clone + install
git clone https://github.com/soneeee22000/csrd-lake.git
cd csrd-lake
make setup       # uv sync --all-extras

# 2. Configure secrets
cp .env.example .env
# edit .env — fill in ANTHROPIC_API_KEY and MISTRAL_API_KEY (Snowflake vars optional)

# 3. Sanity check (no external services needed)
make smoke       # pytest -m smoke -v
make ci          # full lint + mypy + test suite

# 4. Real-LLM extraction smoke test (~$0.10 per run)
#    A pre-downloaded sample is shipped at data/samples/.
make verify-llm PDF=data/samples/lvmh-2024.pdf TICKER=MC.PA TOPIC=E1
# → prints every extracted ESRSMetric with confidence, source citation, routing
# → on Windows without `make` / `uv` on PATH:
#    .venv/Scripts/python.exe -m csrd_lake.extraction.cli --pdf data/samples/lvmh-2024.pdf --ticker MC.PA --topic E1

# 5. Real-data batch — 3 PDFs × 5 ESRS topics → DuckDB warehouse (~$1.50, ~7 min)
#    PDFs are already on disk under data/raw/; the batch CLI runs the LLM
#    fallback chain, streams metrics into DuckDB, archives JSON per company.
make extract-batch    # uv run python -m csrd_lake.extraction.batch ...

# 6. Build the marts (DuckDB local target)
make dbt-build        # cd dbt_project && DBT_TARGET=duckdb uv run dbt deps && seed && run

# 7. Refresh the dashboard JSON snapshot from the warehouse
make export-dashboard # writes dashboard/lib/data/disclosures.json

# Or chain 5-7 in one shot:
make real-data-pipeline

# 8. Validate the same models against a real Snowflake account
#    (requires SNOWFLAKE_PRIVATE_KEY_PATH in .env; see scripts/generate_snowflake_keypair.py)
uv run python scripts/bootstrap_snowflake.py --truncate
uv run python scripts/dbt_run.py deps seed run test --target dev

# 9. Re-export the dashboard snapshot from Snowflake instead of DuckDB.
#    Output is byte-identical (same content, same ORDER BY); only the JSON's
#    `warehouse` field changes — Vercel still serves the static snapshot.
uv run python scripts/export_dashboard_data.py --source snowflake
```

## Project layout

```
csrd-lake/
├── src/csrd_lake/
│   ├── extraction/          schemas.py · confidence.py · prompts.py · llm.py
│   ├── ingestion/           manifest.py · downloader.py · data/cac40.toml
│   └── warehouse/           ddl.sql · loader.py
├── airflow/dags/
│   └── csrd_lake.py         TaskFlow DAG with ingest / extract / load groups
├── dbt_project/
│   ├── models/staging/      stg_disclosure (view, dedupes on natural key)
│   ├── models/marts/        dim_company, dim_metric, dim_period, fact_disclosure,
│   │                        mart_disclosure_published, mart_disclosure_review_queue
│   ├── tests/               metric-value-in-source, confidence-in-[0,1], disjoint
│   └── seeds/               companies, ESRS metrics, periods
├── tests/                   168 pytest cases (mirrors src/, AST-tests for DAG + dbt + dashboard)
├── scripts/
│   ├── bootstrap_snowflake.py     Run DDL + load extracted metrics into Snowflake (key-pair auth)
│   ├── generate_snowflake_keypair.py  PKCS#8 keypair generator + ALTER USER SQL printer
│   ├── dbt_run.py                 dotenv-loading dbt wrapper (forwards args to dbt)
│   └── export_dashboard_data.py   Query DuckDB → write dashboard/lib/data/disclosures.json
├── dashboard/
│   ├── app/                 Next.js 16 routes — / (landing) · /companies · /company/[ticker] · /portfolio
│   ├── components/          Card / Badge / MetricTable / ConfidenceBadge primitives
│   └── lib/data/disclosures.json  Build-time JSON snapshot the dashboard imports
├── docs/
│   ├── PRD.md               Source of truth for requirements
│   ├── PROJECT_CONTEXT.md   Plain-language guide: why · what · how · honest scope · CV pointers
│   └── PORTABILITY.md       Snowflake↔Synapse, Airflow↔ADF, Claude↔Azure OpenAI
├── docker-compose.yml       Airflow 2.10 + Postgres metadata
├── pyproject.toml           Pinned deps (uv-managed)
└── Makefile                 setup · lint · test · smoke · ci · verify-llm · extract-batch · dbt-build · export-dashboard · real-data-pipeline · demo
```

## Methodology + test conditions

The `/moat-check` gate (2026-04-30) killed the original "replaces €40-80k MSCI subscription" hero metric on three grounds:

1. **MSCI's value isn't PDF parsing** — they sell curated ratings + 11K-issuer coverage + 4,000 datapoints/issuer with analyst curation. CSRD-Lake replicates the cheapest part of MSCI's stack only.
2. **Pricing was off by 5-10×** — MSCI's SEC-filed Form ADV 2A pricing band is $5K-$2M/year. Banks at portfolio scale pay $200K-$500K, not €40-80K.
3. **Briink (Berlin) already sells the exact PDF→ESRS extraction at €195/month** with fine-tuned LLMs they claim are >30% more accurate than ChatGPT, plus SOC 2 audit trails.

The README, code comments, dbt SQL, and DAG file are anti-regression-tested for the killed phrasing. See `tests/test_dag_structure.py::test_does_not_reintroduce_killed_claims` and `tests/test_dbt_project_structure.py::test_no_killed_claims_in_sql`.

The current pitch language is **"reference implementation of the Capgemini Sustainability Data Hub / PwC ESG Reporting Manager pattern"** — verifiable, defensible, and aligned with the actual French G-SIB consulting market in 2026.

## Portability

This pipeline is built on Snowflake + Airflow + Claude. The architectural pattern is portable:

| Source choice | Maps to                                                                          |
| ------------- | -------------------------------------------------------------------------------- |
| Snowflake     | Synapse Dedicated SQL Pools / Microsoft Fabric Warehouse / BigQuery / Databricks |
| Airflow       | Azure Data Factory / Prefect / AWS Step Functions                                |
| Claude API    | Azure OpenAI (private) / Bedrock Claude / Vertex AI Claude                       |
| dbt-snowflake | dbt-synapse / dbt-fabric / dbt-bigquery / dbt-databricks                         |

See [`docs/PORTABILITY.md`](docs/PORTABILITY.md) for the detailed mapping with bank-stack-specific notes.

## Demo

The animated walkthrough at the top of this README shows home → per-company ESG profile → portfolio rollup. Static screenshots of each page are in [`dashboard/public/screenshots/`](dashboard/public/screenshots/).

A 90-second narrated Loom walkthrough showing the live Snowflake schema, dbt lineage graph, and a sample LLM extraction is planned for v1.1 (after the gold-set hand-verification adds defensible per-metric accuracy numbers).

## License

MIT — see [`LICENSE`](LICENSE).

## Author

Built by [**Pyae Sone Kyaw (Seon)**](https://pseonkyaw.dev) — Cloud Data Engineer, Data Science, AI. Available for freelance subcontract missions in Paris (auto-entrepreneur, SIRET registered).

- LinkedIn: [pyae-sone-kyaw](https://linkedin.com/in/pyae-sone-kyaw)
- GitHub: [@soneeee22000](https://github.com/soneeee22000)
- Portfolio: [pseonkyaw.dev](https://pseonkyaw.dev)
