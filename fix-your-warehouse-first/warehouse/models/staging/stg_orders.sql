-- The order book, typed. One row per order, always.
select
    cast(order_id as integer) as order_id,
    cast(customer_id as integer) as customer_id,
    cast(order_date as date) as order_date,
    cast(amount_eur as double) as amount_eur,
    status
from {{ ref('orders') }}
