# Portability — bank-stack mapping for CSRD-Lake

CSRD-Lake is built on **Snowflake + Apache Airflow + Anthropic Claude + dbt-snowflake**. The architectural pattern is independent of those specific products — what makes it portable is the layered separation between pure-logic Python modules and the orchestration/warehouse adapters.

This document maps the reference stack onto the three vendor stacks French G-SIBs and their consulting partners actually run.

---

## At-a-glance

| Layer                        | Reference stack (this repo)              | Microsoft Azure stack                                             | AWS stack                 | GCP stack                        |
| ---------------------------- | ---------------------------------------- | ----------------------------------------------------------------- | ------------------------- | -------------------------------- |
| **Orchestration**            | Apache Airflow 2.10 (Docker Compose)     | Azure Data Factory + Synapse Pipelines                            | AWS Step Functions / MWAA | Cloud Composer (managed Airflow) |
| **Warehouse**                | Snowflake                                | Synapse Dedicated SQL Pools / Microsoft Fabric Warehouse          | Redshift / Athena+Glue    | BigQuery                         |
| **dbt adapter**              | `dbt-snowflake`                          | `dbt-synapse` / `dbt-fabric`                                      | `dbt-redshift`            | `dbt-bigquery`                   |
| **LLM (extraction primary)** | Anthropic Claude API (claude-sonnet-4-6) | Azure OpenAI Service (private endpoint) / Azure AI Foundry Claude | Bedrock Claude            | Vertex AI Claude                 |
| **LLM (fallback)**           | Mistral La Plateforme                    | Azure AI Foundry Mistral                                          | Bedrock Mistral           | Vertex AI Mistral                |
| **Object storage (PDFs)**    | Local volume (`/data/raw`)               | Azure Blob Storage / ADLS Gen2                                    | S3                        | GCS                              |
| **Secrets**                  | `.env` (local)                           | Azure Key Vault                                                   | AWS Secrets Manager       | Secret Manager                   |
| **Container runtime**        | Docker Compose                           | Azure Container Apps / AKS                                        | ECS / Fargate / EKS       | Cloud Run / GKE                  |

---

## Stack-by-stack migration notes

### Migrating to Azure (most common French-bank stack)

This is the most likely target — Pyae's prior Cloud Data Engineering experience at Floware was Azure-native (Azure Batch + Blob + Functions + PowerBI), and BNP Paribas, Société Générale, and Crédit Agricole all run significant Azure footprints.

1. **Snowflake → Synapse Dedicated SQL Pools** (or **Fabric Warehouse**)
   - DDL in `src/csrd_lake/warehouse/ddl.sql` is ANSI-compatible; only `IDENTITY(1,1)` syntax differs (Synapse uses the same syntax — minimal change). `NUMBER(28,6)` → `DECIMAL(28,6)`. `TIMESTAMP_TZ` → `DATETIMEOFFSET`.
   - dbt: replace `dbt-snowflake` with `dbt-synapse` (or `dbt-fabric`). Surrogate-key macros from `dbt_utils` work unchanged.
   - Connection: `profiles.yml` switches `type: snowflake` → `type: synapse` with the appropriate `host`, `database`, `authentication: ActiveDirectoryServicePrincipal` for Service Principal auth.

2. **Airflow → Azure Data Factory**
   - The `csrd_lake_dag` task structure (ingest → extract → load) maps 1:1 to ADF Pipelines with three sub-Pipelines. ADF's "ForEach" activity replaces `.expand()` for dynamic task mapping.
   - Custom Python logic (`download_pdf`, `extract_esrs_metrics`, `load_metrics`) runs as **Azure Function Activities** invoked by the Pipeline. The pure-logic packages under `src/csrd_lake/` are deployable as a single Function App with three HTTP-triggered functions.
   - SnowflakeHook → Synapse linked service; Airflow XCom → Pipeline Variables.

3. **Anthropic Claude → Azure OpenAI Service** (private endpoint)
   - The Claude SDK call in `src/csrd_lake/extraction/llm.py::_call_claude` is replaced with an Azure OpenAI client targeting a private endpoint inside the bank's VNet. Tool-use API is supported on the Azure deployment of Claude (via Azure AI Foundry).
   - Pydantic schemas in `src/csrd_lake/extraction/schemas.py` and the prompt template in `src/csrd_lake/extraction/prompts.py` are LLM-agnostic and unchanged.
   - For data-sovereignty-strict deployments, swap to `azure-openai` for an Azure-hosted GPT-4o variant — lose Claude's specific strengths but gain in-VPC-only inference.

4. **Local PDFs → ADLS Gen2**
   - `download_pdf` writes to `target: Path`; swap the `pathlib` write with `azure.storage.blob.BlobClient.upload_blob`. The function signature stays sync; the SDK is sync-friendly.
   - The Airflow DAG's `RAW_DIR = Path("/opt/airflow/data/raw")` becomes a `BlobServiceClient` reference, with PDF byte streams passed through XCom paths.

5. **Secrets → Key Vault**
   - `.env` env vars (`ANTHROPIC_API_KEY`, `SNOWFLAKE_PASSWORD`) become Key Vault secrets referenced by the Function App's environment. ADF Linked Services pull from Key Vault directly.

**Realistic migration timeline** for a single Cloud Data Engineer with Pyae's profile: **~2 weeks** for the lift-and-shift to Synapse + ADF + Azure OpenAI, including dbt model rewrites + ADF pipeline construction. **~4 weeks** for full integration into a bank's existing Synapse data platform with their dim_customer / dim_facility joins.

---

### Migrating to AWS

Less common at French G-SIBs but realistic for fintech / payments clients.

- **Snowflake → Redshift**: dbt-snowflake → dbt-redshift. `NUMBER` → `NUMERIC`. `dim_*` materialization stays as `table`; `mart_*` may benefit from `materialized=table` with `dist_key=company_id` for join performance.
- **Airflow → Step Functions**: TaskFlow DAGs translate cleanly to ASL (Amazon States Language) state machines. `.expand()` → Step Functions `Map` state with `MaxConcurrency`. SnowflakeHook → Lambda invoking the Redshift Data API.
- **Anthropic Claude → Amazon Bedrock Claude**: same Pydantic schemas; SDK swap from `anthropic` to `boto3.client('bedrock-runtime')`. Tool-use parameters are passed via Bedrock's converse API.
- **Local PDFs → S3**: write paths become `s3://csrd-lake-raw/<ticker>-<year>.pdf`.

---

### Migrating to GCP

- **Snowflake → BigQuery**: dbt-snowflake → dbt-bigquery. BigQuery doesn't have `IDENTITY` columns — surrogate keys via `dbt_utils.generate_surrogate_key` already work. `NUMBER(28,6)` → `BIGNUMERIC`.
- **Airflow → Cloud Composer**: Composer IS managed Airflow — the DAG file is portable as-is. Only the SnowflakeHook needs replacing with `BigQueryHook`.
- **Anthropic Claude → Vertex AI Claude**: same SDK pattern; `vertexai.generative_models.GenerativeModel("claude-sonnet-4-6@anthropic")`.
- **Local PDFs → GCS**: write paths become `gs://csrd-lake-raw/...`.

This is actually the **lightest-touch migration** if a bank already runs on GCP — Cloud Composer keeps Airflow, Vertex AI keeps Claude.

---

## What's intentionally NOT portable

- **Airflow ↔ Prefect / Dagster**: TaskFlow API is Airflow-specific. A migration would rewrite the DAG file (~2 days). The pure-logic Python modules transfer unchanged.
- **dbt → Native warehouse SQL**: dbt's `ref()` / `source()` / `dbt_utils.*` macros assume dbt as the build engine. A migration to native SQL stored procedures or scheduled queries loses lineage + testing — not recommended.
- **Pydantic v2 schemas**: tightly coupled to Python. If a bank standardizes on Java + Spark + Apache Iceberg, the extraction layer needs a Spark reimplementation — but the Airflow DAG and the Snowflake DDL are reusable as-is.

---

## How to extend the manifest beyond CAC 40

The starter manifest covers 10 CAC 40 companies. Adding DAX 40 / IBEX 35 / FTSE 100:

1. Append entries to `src/csrd_lake/ingestion/data/cac40.toml` (rename if multi-index becomes the norm — `eu_indices.toml` is the v2 path).
2. Mirror the additions into `dbt_project/seeds/companies_seed.csv`.
3. Update `tests/test_manifest.py::test_cac40_has_ten_companies` and `tests/test_dbt_project_structure.py::test_companies_seed_has_ten_rows` for the new count.
4. For DAX 40 (German reports), also add `de` to the `Language` enum in `src/csrd_lake/extraction/schemas.py` and to the `accepted_values` test in `dbt_project/models/staging/_sources.yml`.

---

## See also

- [`docs/PRD.md`](PRD.md) — Source of truth for requirements
- [`README.md`](../README.md) — Project overview + quickstart
- [`src/csrd_lake/warehouse/ddl.sql`](../src/csrd_lake/warehouse/ddl.sql) — Snowflake DDL (the most stack-specific file in the repo)
