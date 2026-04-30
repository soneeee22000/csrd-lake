{{
    config(
        materialized='table',
        tags=['marts', 'dimension', 'company']
    )
}}

-- DIM_COMPANY — sourced from the seeded manifest. One row per company.
-- Surrogate key (`company_id`) generated for stable joins from facts.

with seeded as (

    select
        ticker,
        name,
        sector,
        country,
        ir_page_url,
        language
    from {{ ref('companies_seed') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['ticker']) }} as company_id,
    ticker,
    name,
    sector,
    country,
    ir_page_url,
    language
from seeded
