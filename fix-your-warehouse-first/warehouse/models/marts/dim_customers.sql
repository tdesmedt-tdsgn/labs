-- One row per customer. That is the intent, and the intent is the whole
-- problem: nothing in this file enforces it. The filter below is the only
-- thing standing between "customer dimension" and "customer history table",
-- and it is exactly the line that goes missing in a hurry.
select
    customer_id,
    region,
    valid_from
from {{ ref('stg_customers') }}
{% if var('scenario') == 'fixed' %}
where is_current
{% endif %}
