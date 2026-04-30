{{
    config(
        materialized='table',
        tags=['marts', 'dimension', 'period']
    )
}}

-- DIM_PERIOD — one row per fiscal year (FY2024 in v1; v2 may extend).

with seeded as (

    select
        fiscal_year,
        period_start,
        period_end,
        reporting_basis
    from {{ ref('periods_seed') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['fiscal_year']) }} as period_id,
    fiscal_year,
    period_start,
    period_end,
    reporting_basis
from seeded
