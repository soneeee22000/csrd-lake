"""Corporate sustainability PDF ingestion.

Pure-logic library that the Airflow `ingest_pdfs` DAG composes:
- manifest.py    — Pydantic model + TOML loader for the company manifest
- downloader.py  — httpx + tenacity PDF download with idempotency and PDF validation

The starter manifest covers 10 CAC 40 companies. DAX 40 + IBEX 35 may extend
in a v2 manifest (PRD §8 marks them as stretch goals).
"""
