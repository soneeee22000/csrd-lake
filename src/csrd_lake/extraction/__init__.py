"""ESRS metric extraction from corporate sustainability PDFs.

Layers:
- schemas.py    — Pydantic models for ESRS metrics
- confidence.py — confidence scoring logic
- llm.py        — Claude / Mistral extraction calls
- cli.py        — `python -m csrd_lake.extraction.cli` entrypoint
"""
