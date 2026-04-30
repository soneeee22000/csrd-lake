# CSRD-Lake

> **End-to-end CSRD/ESRS data pipeline reference implementation** — Snowflake star schema + dbt models + Airflow orchestration + multilingual GenAI extraction with source citation and audit lineage. Same architectural pattern Capgemini's Sustainability Data Hub and PwC's ESG Reporting Manager deploy at French banks today.
>
> Built solo as a portfolio piece. Open-source under MIT.

---

## Status

🚧 **Currently scaffolded — Weekend 1 build starts 2026-05-02.** This README will be updated with hero metrics, screenshots, and the Loom walkthrough once the build is complete (target: 2026-05-11).

---

## What this is

CSRD-Lake ingests corporate sustainability PDFs from CAC 40 / DAX 40 issuers, extracts 80+ ESRS metrics per company using Claude Sonnet (with Mistral Large as fallback), validates each extraction against Pydantic schemas with confidence scoring, and lands the results in a Snowflake star schema modeled with dbt.

Every extracted metric carries:

- A **confidence score** in `[0.0, 1.0]` — values below `0.80` route automatically to a human-review queue (`mart_disclosure_review_queue`) instead of the published mart.
- A **source citation** — page number + verbatim snippet from the source PDF, enforced as a hard requirement of the extraction schema.
- A **language tag** (`fr` or `en` in v1) verified against the actual content (not just the file metadata).
- A **model tag** identifying which LLM produced the value, for per-model accuracy reporting.

The output is consumable via:

1. **Snowflake SQL** — direct query against `marts.fact_disclosure` and the published / review-queue marts
2. **dbt docs site** — auto-generated lineage and model documentation
3. **Next.js dashboard** — per-company ESG profile + synthetic 50-corporate loan-book rollup demo

## What this is NOT

- ❌ A product replacing MSCI / Sustainalytics / Bloomberg ESG / Briink / any other ESG data vendor
- ❌ A claim that any bank should buy this instead of their existing ESG data feeds
- ❌ A real bank loan book (the loan-book demo is synthetic and labeled as such)
- ❌ A complete CSRD compliance solution (single framework only — no TCFD/ISSB/Pillar 3 cross-walks in v1)

## Why this exists

French G-SIBs and the consulting practices supporting them (Capgemini Sustainability Data Hub, Deloitte CSRD 360 Navigator, PwC ESG Reporting Manager, KPMG, EY) are actively staffing freelance Cloud Data Engineers fluent in Snowflake/dbt/Airflow + GenAI extraction for CSRD wave-1 reporting in 2026. CSRD-Lake demonstrates that pattern end-to-end as a single open-source reference implementation.

## Architecture

```
CAC 40 / DAX 40 IR pages
        │
        ▼  (Airflow ingest_pdfs DAG)
   /data/raw/*.pdf
        │
        ▼  (Airflow extract_esrs DAG)
Claude Sonnet API + Pydantic ESRS schemas
        │  (with Mistral Large fallback + confidence scoring + source citation)
        ▼
 Snowflake raw.disclosure_extracted
        │
        ▼  (dbt run + dbt test)
 Snowflake staging.stg_disclosure
        │
        ▼  (dbt model)
 Snowflake marts.fact_disclosure + dim_company + dim_metric + dim_period
        │
        ├─► confidence < 0.80 → marts.mart_disclosure_review_queue
        │
        └─► confidence ≥ 0.80 → marts.mart_disclosure_published
                                        │
                                        ▼
                               Next.js dashboard on Vercel
```

See `docs/PRD.md` for the full requirements, edge-case handling, and quality gates.

## Getting started

```bash
# Prerequisites: Python 3.12, Docker Compose, uv, Snowflake free trial account, Anthropic + Mistral API keys

# 1. Clone + install
git clone https://github.com/soneeee22000/csrd-lake.git
cd csrd-lake
make setup

# 2. Configure secrets
cp .env.example .env
# edit .env — fill in ANTHROPIC_API_KEY, MISTRAL_API_KEY, SNOWFLAKE_*

# 3. Verify smoke test (no external services needed)
make smoke

# 4. Start Airflow + Postgres
make services

# 5. Run the demo
make demo
# → opens Airflow UI at http://localhost:8080 (login: airflow/airflow)
# → triggers ingest_pdfs → extract_esrs → load_to_snowflake → dbt run/test
# → dashboard at http://localhost:3000 once Weekend 2 ships
```

## Tech stack

| Layer             | Choice                                                   |
| ----------------- | -------------------------------------------------------- |
| Orchestration     | Apache Airflow 2.10 (Docker Compose)                     |
| Extraction LLM    | Claude Sonnet (primary) + Mistral Large (fallback)       |
| Schema validation | Pydantic v2                                              |
| Warehouse         | Snowflake (free trial; DuckDB fallback documented)       |
| Transformations   | dbt-core 1.9 with `dbt-snowflake` adapter                |
| Dashboard         | Next.js 16 + Vercel (Streamlit fallback if budget tight) |
| Tests             | pytest + dbt tests + custom data-quality assertions      |
| CI                | GitHub Actions (lint + mypy + pytest + dbt parse)        |

## Portability

This pipeline is built on Snowflake + Airflow + Claude, but the architectural pattern is portable to:

| Source choice | Maps to                                                                          |
| ------------- | -------------------------------------------------------------------------------- |
| Snowflake     | Synapse Dedicated SQL Pools / Microsoft Fabric Warehouse / BigQuery / Databricks |
| Airflow       | Azure Data Factory / Prefect / AWS Step Functions                                |
| Claude API    | Azure OpenAI (private) / Bedrock Claude / Vertex AI Claude                       |
| dbt-snowflake | dbt-synapse / dbt-fabric / dbt-bigquery / dbt-databricks                         |

See `docs/PORTABILITY.md` (will be populated in Weekend 2) for the detailed mapping and bank-stack-specific notes.

## Methodology + test conditions

⚠️ **All numeric claims in this README will be added once the build is complete (target 2026-05-11)**, with explicit test conditions per claim:

- "X% accuracy" claims → gold-set size, language distribution, metric distribution, verification method
- "N PDFs" claims → source list (CAC 40 / DAX 40 tickers), date range, exclusions
- "<X min cold-start" claims → hardware, network, excluded steps

This is enforced by the project's quality gates (see `docs/PRD.md` §10).

## License

MIT — see `LICENSE`.

## Author

Built by [Pyae Sone Kyaw](https://pseonkyaw.dev) — Cloud Data Engineer, Data Science, AI. Available for freelance subcontract missions in Paris (auto-entrepreneur, SIRET registered).

- LinkedIn: [pyae-sone-kyaw](https://linkedin.com/in/pyae-sone-kyaw)
- GitHub: [@soneeee22000](https://github.com/soneeee22000)
