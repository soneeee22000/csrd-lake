-- Custom test: every fact_disclosure row's source_snippet must contain
-- the extracted value as text. Catches LLM hallucinations where a value
-- is invented but the snippet doesn't actually support it.
--
-- Returns failing rows (PASS = empty result set).
--
-- Numeric values are checked with three common renderings:
--   - raw integer ("147500")
--   - thousand-separated ("147,500")
--   - decimal-prefixed ("147500.00")
--
-- Text values use a case-insensitive substring match.

with fact as (

    select
        disclosure_id,
        value_numeric,
        value_text,
        source_snippet
    from {{ ref('fact_disclosure') }}

),

flagged as (

    select
        disclosure_id,
        value_numeric,
        value_text,
        source_snippet,
        case
            -- Numeric metric: snippet must contain a recognizable rendering
            when value_numeric is not null then
                not (
                    contains(replace(replace(source_snippet, ',', ''), ' ', ''),
                             cast(cast(value_numeric as integer) as varchar))
                    or contains(source_snippet, cast(value_numeric as varchar))
                )
            -- Text metric: snippet must contain the value (case-insensitive)
            when value_text is not null then
                position(lower(value_text) in lower(source_snippet)) = 0
            -- Should never happen — Pydantic enforces exactly one populated.
            else true
        end as is_failing
    from fact

)

select
    disclosure_id,
    value_numeric,
    value_text,
    source_snippet
from flagged
where is_failing
