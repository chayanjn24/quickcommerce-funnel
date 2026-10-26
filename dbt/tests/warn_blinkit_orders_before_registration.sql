-- known problem in the source, kept as a warning
{{ config(severity = 'warn') }}
select customer_id, registered_on, first_order_at
from {{ ref('dim_customers') }}
where registered_after_first_order
