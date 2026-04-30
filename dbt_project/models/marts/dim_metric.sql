{{
    config(
        materialized='table',
        tags=['marts', 'dimension', 'metric']
    )
}}

-- DIM_METRIC — the canonical ESRS catalog (≤80 metrics across 5 topics in v1).
-- Mirrors `csrd_lake.extraction.prompts.ESRS_METRIC_CATALOG` so the LLM
-- prompts and the warehouse stay in sync.

with seeded as (

    select
        esrs_topic,
        esrs_disclosure,
        metric_name,
        unit
    from {{ ref('esrs_metrics_seed') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['esrs_disclosure', 'metric_name']) }} as metric_id,
    esrs_topic,
    esrs_disclosure,
    metric_name,
    unit,
    true as mandatory_flag
from seeded
