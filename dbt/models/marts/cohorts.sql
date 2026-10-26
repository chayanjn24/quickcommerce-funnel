-- cohorts by first order month, not registration date (many customers ordered before they "registered")
with orders as (
    select
        o.customer_id,
        date_trunc('month', o.ordered_at)::date  as order_month,
        c.cohort_month,
        o.order_total
    from {{ ref('fct_orders') }} o
    join {{ ref('dim_customers') }} c using (customer_id)
),

cohort_size as (
    select cohort_month, count(*) as customers
    from {{ ref('dim_customers') }}
    where has_ordered
    group by 1
),

last_month as (
    select max(order_month) as m from orders
)

select
    o.cohort_month,
    (extract(year from age(o.order_month, o.cohort_month)) * 12
        + extract(month from age(o.order_month, o.cohort_month)))::int  as months_since_first,
    s.customers                                                         as cohort_customers,
    count(distinct o.customer_id)                                       as active_customers,
    round(count(distinct o.customer_id)::numeric / s.customers, 4)      as retention,
    count(*)                                                            as orders,
    sum(o.order_total)                                                  as revenue
from orders o
join cohort_size s using (cohort_month)
cross join last_month
where o.order_month < last_month.m   -- last month is partial
group by 1, 2, 3
