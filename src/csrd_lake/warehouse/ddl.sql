-- CSRD-Lake — Snowflake star schema DDL.
--
-- This file is the source of truth for the warehouse shape. dbt models in
-- `dbt_project/` re-create equivalent schemas via dbt-snowflake; this DDL is
-- run once at project bootstrap to create the database, schemas, and the
-- raw landing table the Python loader writes to.
--
-- Run order:
--   1. `CREATE DATABASE CSRD_LAKE` (manual, once)
--   2. `USE DATABASE CSRD_LAKE`
--   3. Run this file end-to-end via Snowflake worksheet or `snowsql -f`.
--
-- Idempotent: every CREATE uses IF NOT EXISTS.
-- ─────────────────────────────────────────────────────────────────────
-- Schemas
-- ─────────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS RAW;

-- landing zone for Python loader
CREATE SCHEMA IF NOT EXISTS STAGING;

-- dbt-managed cleansing layer
CREATE SCHEMA IF NOT EXISTS MARTS;

-- dbt-managed published marts
-- ─────────────────────────────────────────────────────────────────────
-- RAW landing table — what the Python extraction pipeline writes into.
-- The shape mirrors `csrd_lake.extraction.schemas.ESRSMetric` 1:1 so the
-- loader is a straightforward column mapping.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS RAW.DISCLOSURE_EXTRACTED (
  -- Identity
  company_ticker VARCHAR(10) NOT NULL,
  fiscal_year SMALLINT NOT NULL,
  -- ESRS taxonomy
  esrs_topic VARCHAR(2) NOT NULL, -- E1, E2, E3, S1, G1
  esrs_disclosure VARCHAR(20) NOT NULL, -- e.g. 'E1-6'
  metric_name VARCHAR(200) NOT NULL,
  -- Value (exactly one of value_numeric / value_text is populated)
  value_numeric NUMBER (28, 6),
  value_text VARCHAR(500),
  unit VARCHAR(50),
  -- Audit + confidence
  confidence_score NUMBER (4, 3) NOT NULL, -- [0.000, 1.000]
  source_page INTEGER NOT NULL,
  source_snippet VARCHAR(500) NOT NULL,
  language VARCHAR(2) NOT NULL, -- 'fr' | 'en'
  -- Provenance
  extraction_model VARCHAR(50) NOT NULL, -- 'claude-sonnet-4-6' | 'mistral-large-latest'
  extraction_timestamp TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

-- The dbt staging layer treats this composite as the natural key for
-- de-duplication when the same extraction is re-run.
CREATE INDEX IF NOT EXISTS IDX_RAW_DISCLOSURE_NATURAL ON RAW.DISCLOSURE_EXTRACTED (
  company_ticker,
  fiscal_year,
  esrs_disclosure,
  extraction_model
);

-- ─────────────────────────────────────────────────────────────────────
-- MARTS dimensions (populated by dbt seeds from the manifest + catalog).
-- Listed here so a fresh Snowflake account has the full schema after one
-- run; dbt's CREATE OR REPLACE will manage them after that.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS MARTS.DIM_COMPANY (
  company_id INTEGER NOT NULL IDENTITY (1, 1),
  ticker VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  sector VARCHAR(50) NOT NULL,
  country VARCHAR(2) NOT NULL,
  ir_page_url VARCHAR(500) NOT NULL,
  language VARCHAR(2) NOT NULL,
  PRIMARY KEY (company_id)
);

CREATE TABLE IF NOT EXISTS MARTS.DIM_METRIC (
  metric_id INTEGER NOT NULL IDENTITY (1, 1),
  esrs_topic VARCHAR(2) NOT NULL,
  esrs_disclosure VARCHAR(20) NOT NULL,
  metric_name VARCHAR(200) NOT NULL,
  unit VARCHAR(50),
  mandatory_flag BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (metric_id),
  UNIQUE (esrs_disclosure, metric_name)
);

CREATE TABLE IF NOT EXISTS MARTS.DIM_PERIOD (
  period_id INTEGER NOT NULL IDENTITY (1, 1),
  fiscal_year SMALLINT NOT NULL UNIQUE,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  reporting_basis VARCHAR(20) NOT NULL DEFAULT 'CSRD/ESRS',
  PRIMARY KEY (period_id)
);

-- ─────────────────────────────────────────────────────────────────────
-- MARTS.FACT_DISCLOSURE is the canonical fact table the dbt models build.
-- Defined here as documentation / fallback; dbt's `marts/fact_disclosure.sql`
-- is the authoritative builder during normal operation.
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS MARTS.FACT_DISCLOSURE (
  disclosure_id INTEGER NOT NULL IDENTITY (1, 1),
  company_id INTEGER NOT NULL,
  metric_id INTEGER NOT NULL,
  period_id INTEGER NOT NULL,
  value_numeric NUMBER (28, 6),
  value_text VARCHAR(500),
  unit VARCHAR(50),
  confidence_score NUMBER (4, 3) NOT NULL,
  source_page INTEGER NOT NULL,
  source_snippet VARCHAR(500) NOT NULL,
  language VARCHAR(2) NOT NULL,
  extraction_model VARCHAR(50) NOT NULL,
  extraction_timestamp TIMESTAMP_TZ NOT NULL,
  human_approved BOOLEAN, -- NULL = not yet reviewed
  PRIMARY KEY (disclosure_id),
  FOREIGN KEY (company_id) REFERENCES MARTS.DIM_COMPANY (company_id),
  FOREIGN KEY (metric_id) REFERENCES MARTS.DIM_METRIC (metric_id),
  FOREIGN KEY (period_id) REFERENCES MARTS.DIM_PERIOD (period_id)
);
