-- known problem in the source, kept as a warning
{{ config(severity = 'warn') }}
select customer_id, total_orders_reported, orders
from {{ ref('dim_customers') }}
where total_orders_reported <> orders
