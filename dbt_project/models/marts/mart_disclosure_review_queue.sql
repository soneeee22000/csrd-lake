{{
    config(
        materialized='table',
        tags=['marts', 'reporting', 'review_queue']
    )
}}

-- MART_DISCLOSURE_REVIEW_QUEUE — low-confidence and not-yet-approved
-- metrics, surfaced to a human reviewer. Same shape as the published mart
-- so the dashboard can switch between views without schema drift.

select
    fact.disclosure_id,
    company.ticker          as company_ticker,
    company.name            as company_name,
    company.sector,
    company.country,
    metric.esrs_topic,
    metric.esrs_disclosure,
    metric.metric_name,
    period.fiscal_year,
    fact.value_numeric,
    fact.value_text,
    fact.unit,
    fact.confidence_score,
    fact.source_page,
    fact.source_snippet,
    fact.language,
    fact.extraction_model,
    fact.extraction_timestamp,
    coalesce(fact.human_approved, false) as human_approved
from {{ ref('fact_disclosure') }} as fact
inner join {{ ref('dim_company') }} as company on fact.company_id = company.company_id
inner join {{ ref('dim_metric') }}  as metric  on fact.metric_id  = metric.metric_id
inner join {{ ref('dim_period') }}  as period  on fact.period_id  = period.period_id
where
    fact.confidence_score < {{ var('confidence_threshold') }}
    and (fact.human_approved is null or fact.human_approved = false)
