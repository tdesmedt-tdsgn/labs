-- Completed orders, enriched with the customer's region. This is the table an
-- assistant would be pointed at, and it is written correctly: the join is on
-- the right key and the status filter is right. It inherits the duplication
-- from the dimension anyway, because a join to a non-unique key fans out.
select
    o.order_id,
    o.customer_id,
    c.region,
    o.order_date,
    o.amount_eur as revenue_eur,
    o.status
from {{ ref('stg_orders') }} o
join {{ ref('dim_customers') }} c
  on o.customer_id = c.customer_id
where o.status = 'completed'
