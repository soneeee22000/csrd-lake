{{
    config(
        materialized='table',
        tags=['marts', 'reporting', 'published']
    )
}}

-- MART_DISCLOSURE_PUBLISHED — the published mart that the Next.js
-- dashboard reads from. PRD Story 4 routing rule: only metrics with
-- confidence ≥ {{ var('confidence_threshold') }} (or human_approved=TRUE)
-- land here. Everything else is in `mart_disclosure_review_queue`.

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
    fact.extraction_timestamp
from {{ ref('fact_disclosure') }} as fact
inner join {{ ref('dim_company') }} as company on fact.company_id = company.company_id
inner join {{ ref('dim_metric') }}  as metric  on fact.metric_id  = metric.metric_id
inner join {{ ref('dim_period') }}  as period  on fact.period_id  = period.period_id
where
    fact.confidence_score >= {{ var('confidence_threshold') }}
    or fact.human_approved = true
