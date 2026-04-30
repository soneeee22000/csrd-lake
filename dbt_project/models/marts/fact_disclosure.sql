{{
    config(
        materialized='table',
        tags=['marts', 'fact', 'disclosure']
    )
}}

-- FACT_DISCLOSURE — the canonical fact table. Joins the deduplicated
-- staging layer to the three dimensions on natural keys, exposes
-- surrogate keys for downstream marts and the dashboard, and preserves
-- the audit columns (source_page, source_snippet, extraction_model,
-- extraction_timestamp).

with stg as (

    select * from {{ ref('stg_disclosure') }}

),

dim_company as (

    select company_id, ticker from {{ ref('dim_company') }}

),

dim_metric as (

    select metric_id, esrs_disclosure, metric_name from {{ ref('dim_metric') }}

),

dim_period as (

    select period_id, fiscal_year from {{ ref('dim_period') }}

)

select
    {{ dbt_utils.generate_surrogate_key([
        'stg.company_ticker',
        'stg.fiscal_year',
        'stg.esrs_disclosure',
        'stg.extraction_model'
    ]) }}                                       as disclosure_id,
    dim_company.company_id,
    dim_metric.metric_id,
    dim_period.period_id,
    stg.value_numeric,
    stg.value_text,
    stg.unit,
    stg.confidence_score,
    stg.source_page,
    stg.source_snippet,
    stg.language,
    stg.extraction_model,
    stg.extraction_timestamp,
    cast(null as boolean) as human_approved   -- populated by review-queue workflow
from stg
inner join dim_company on stg.company_ticker = dim_company.ticker
inner join dim_metric  on stg.esrs_disclosure = dim_metric.esrs_disclosure
                         and stg.metric_name   = dim_metric.metric_name
inner join dim_period  on stg.fiscal_year      = dim_period.fiscal_year
