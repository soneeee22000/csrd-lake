-- Custom test: confidence_score must be in [0, 1].
-- Belt-and-braces for the column-level test in marts/_models.yml — kept
-- as a separate file so it shows up as its own test in dbt docs.

select
    disclosure_id,
    confidence_score
from {{ ref('fact_disclosure') }}
where confidence_score < 0 or confidence_score > 1
