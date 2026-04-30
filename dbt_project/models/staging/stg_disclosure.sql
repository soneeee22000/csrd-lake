{{
    config(
        materialized='view',
        tags=['staging', 'disclosure']
    )
}}

-- Staging layer: clean RAW.DISCLOSURE_EXTRACTED, dedupe on natural key
-- by picking the latest extraction_timestamp per
-- (company_ticker, fiscal_year, esrs_disclosure, extraction_model).
--
-- Rationale: re-runs of the extraction DAG land new rows in raw without
-- replacing previous extractions. The marts read from this view, so they
-- always see the most recent extraction per natural key.

with source as (

    select
        company_ticker,
        fiscal_year,
        esrs_topic,
        esrs_disclosure,
        metric_name,
        value_numeric,
        value_text,
        unit,
        confidence_score,
        source_page,
        source_snippet,
        language,
        extraction_model,
        extraction_timestamp
    from {{ source('raw', 'disclosure_extracted') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by company_ticker, fiscal_year, esrs_disclosure, extraction_model
            order by extraction_timestamp desc
        ) as recency_rank
    from source

)

select
    company_ticker,
    fiscal_year,
    esrs_topic,
    esrs_disclosure,
    metric_name,
    value_numeric,
    value_text,
    unit,
    confidence_score,
    source_page,
    source_snippet,
    language,
    extraction_model,
    extraction_timestamp
from ranked
where recency_rank = 1
