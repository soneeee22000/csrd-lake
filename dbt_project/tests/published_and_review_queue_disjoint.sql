-- Custom test: every disclosure_id appears in exactly ONE of
-- mart_disclosure_published or mart_disclosure_review_queue, never both.
--
-- This is the routing invariant for PRD Story 4 — if it fails, the
-- threshold + human_approved logic in the two marts has drifted.

with both as (

    select disclosure_id
    from {{ ref('mart_disclosure_published') }}

    intersect

    select disclosure_id
    from {{ ref('mart_disclosure_review_queue') }}

)

select disclosure_id from both
