-- The CRM export, typed. One row per customer *version*, not per customer:
-- when a customer's region changes, the old row stays and a new one arrives
-- with is_current = true.
select
    cast(customer_id as integer) as customer_id,
    region,
    cast(valid_from as date) as valid_from,
    cast(is_current as boolean) as is_current
from {{ ref('customers') }}
