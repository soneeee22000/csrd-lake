.PHONY: help setup services stop lint format test smoke ci extract dbt-run dbt-test demo clean

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
	uv run pytest -m smoke -v

ci:  ## Everything CI runs
	$(MAKE) lint
	$(MAKE) test

# ── Pipeline ─────────────────────────────────────────────────────────
extract:  ## Run extraction pipeline against sample PDFs
	uv run python -m csrd_lake.extraction.cli --input data/samples --output data/staging

dbt-run:  ## Run dbt models
	cd dbt_project && uv run dbt run --target dev

dbt-test:  ## Run dbt tests
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
