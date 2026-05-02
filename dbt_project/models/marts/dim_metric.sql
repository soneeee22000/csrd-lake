{{
    config(
        materialized='table',
        tags=['marts', 'dimension', 'metric']
    )
}}

-- DIM_METRIC — canonical ESRS catalog UNION any granular sub-disclosures
-- discovered in real extractions.
--
-- The seed (`esrs_metrics_seed`) is the curated core: parent-level metrics
-- the prompt catalog explicitly asks the LLM to find. But corporate reports
-- disclose more granular variants — e.g. TotalEnergies splits E2-4 air
-- pollutants into NMVOC / NOx / SO2 / particulate matter; LVMH splits E3-4
-- water by use case (agricultural / process / value chain). These are
-- legitimate ESRS-compliant disclosures the seed cannot enumerate up front.
--
-- `is_in_catalog = true` for rows from the seed; `false` for auto-discovered
-- rows. Downstream marts can filter to `is_in_catalog = true` if they want
-- the strict catalog view, or accept all rows for the full disclosure surface.

with seeded as (

    select
        esrs_topic,
        esrs_disclosure,
        metric_name,
        unit,
        true as is_in_catalog
    from {{ ref('esrs_metrics_seed') }}

),

discovered as (

    select distinct
        stg.esrs_topic,
        stg.esrs_disclosure,
        stg.metric_name,
        stg.unit,
        false as is_in_catalog
    from {{ ref('stg_disclosure') }} as stg
    left join seeded
        on  stg.esrs_disclosure = seeded.esrs_disclosure
        and stg.metric_name     = seeded.metric_name
    where seeded.metric_name is null

),

unioned as (

    select * from seeded
    union all
    select * from discovered

)

select
    {{ dbt_utils.generate_surrogate_key(['esrs_disclosure', 'metric_name']) }} as metric_id,
    esrs_topic,
    esrs_disclosure,
    metric_name,
    unit,
    -- Catalog rows are mandatory; auto-discovered rows are optional disclosures.
    is_in_catalog as mandatory_flag,
    is_in_catalog
from unioned
