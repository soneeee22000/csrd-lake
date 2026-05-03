.PHONY: help setup services stop lint format test smoke ci verify-llm extract-batch dbt-build export-dashboard real-data-pipeline dbt-run dbt-test demo clean

# Defaults for `make verify-llm` — override on the command line:
#   make verify-llm PDF=data/samples/lvmh-2024.pdf TICKER=MC.PA TOPIC=E1
PDF ?= data/samples/sample.pdf
TICKER ?= MC.PA
TOPIC ?= E1

help:  ## Show this help
	@echo "CSRD-Lake — Makefile commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Install Python deps + dev deps
	uv sync --all-extras

services:  ## Start Airflow + Postgres via Docker Compose
	docker compose up -d

stop:  ## Stop all services
	docker compose down

# ── Quality gates ────────────────────────────────────────────────────
lint:  ## Run ruff + mypy
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src

format:  ## Auto-fix ruff issues
	uv run ruff check --fix src tests
	uv run ruff format src tests

test:  ## Run full test suite with coverage
	uv run pytest

smoke:  ## Run smoke test only (cold-start sanity)
	uv run pytest -m smoke -v --no-cov

ci:  ## Everything CI runs
	$(MAKE) lint
	$(MAKE) test

# ── Pipeline ─────────────────────────────────────────────────────────
verify-llm:  ## Real-LLM smoke test: extract one PDF via Claude+Mistral. PDF=path TICKER=MC.PA TOPIC=E1
	@test -f .env || (echo "  ✗ .env missing — copy .env.example, fill in ANTHROPIC_API_KEY + MISTRAL_API_KEY" && exit 1)
	@test -f $(PDF) || (echo "  ✗ PDF not found at $(PDF) — pass PDF=path/to/your.pdf" && exit 1)
	uv run python -m csrd_lake.extraction.cli --pdf $(PDF) --ticker $(TICKER) --topic $(TOPIC)

extract-batch:  ## Run real-LLM batch across all PDFs in data/raw/ × 5 ESRS topics into local DuckDB
	@test -f .env || (echo "  ✗ .env missing — copy .env.example, fill in ANTHROPIC_API_KEY + MISTRAL_API_KEY" && exit 1)
	uv run python -m csrd_lake.extraction.batch --max-pages 200 --max-prompt-chars 80000 --inter-call-delay 8

dbt-build:  ## Build all dbt models against local DuckDB (seed + run)
	cd dbt_project && DBT_TARGET=duckdb uv run dbt deps
	cd dbt_project && DBT_TARGET=duckdb uv run dbt seed
	cd dbt_project && DBT_TARGET=duckdb uv run dbt run

export-dashboard:  ## Export DuckDB marts to dashboard/lib/data/disclosures.json (commit this file)
	uv run python scripts/export_dashboard_data.py

real-data-pipeline: extract-batch dbt-build export-dashboard  ## End-to-end: real LLM batch -> DuckDB -> dbt marts -> dashboard JSON
	@echo "→ Real-data pipeline complete. cd dashboard && pnpm build to publish."

dbt-run:  ## Run dbt models (Snowflake target)
	cd dbt_project && uv run dbt run --target dev

dbt-test:  ## Run dbt tests (Snowflake target)
	cd dbt_project && uv run dbt test --target dev

demo:  ## Full cold-start demo (PRD Story 3 acceptance test)
	@echo "→ Verifying env"
	@test -f .env || (echo "  .env missing — copy from .env.example" && exit 1)
	@echo "→ Starting services"
	$(MAKE) services
	@echo "→ Waiting for Airflow to be healthy (30s)"
	@sleep 30
	@echo "→ Triggering ingest_pdfs DAG"
	docker compose exec airflow-webserver airflow dags trigger ingest_pdfs
	@echo "→ Demo running. Visit http://localhost:8080 (airflow/airflow)"
	@echo "→ Dashboard at http://localhost:3000 once Weekend 2 ships."

clean:  ## Clean caches + Docker volumes
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov
	rm -rf dbt_project/target dbt_project/dbt_packages dbt_project/logs
	docker compose down -v
