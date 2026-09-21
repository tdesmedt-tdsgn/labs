-- The lineage test: money must survive the joins.
--
-- Column tests check shapes. This one checks the thing a finance director
-- would check by hand, which is that the total at the end of the pipeline is
-- still the total that went into it. It returns rows only when they disagree,
-- and a data test that returns rows fails.
with source_total as (
    select round(sum(amount_eur), 2) as total
    from {{ ref('stg_orders') }}
    where status = 'completed'
),
mart_total as (
    select round(sum(revenue_eur), 2) as total
    from {{ ref('fct_revenue') }}
)
select
    s.total as source_total,
    m.total as mart_total,
    round(m.total - s.total, 2) as difference
from source_total s
cross join mart_total m
where abs(s.total - m.total) > 0.01
