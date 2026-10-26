with orders as (
    select
        scenario,
        user_id,
        count(*)                        as orders,
        sum(basket_inr)                 as gross_inr,
        sum(discount_inr)               as discount_inr
    from {{ ref('stg_experiment__orders') }}
    group by 1, 2
)

select
    u.scenario,
    u.user_id,
    u.variant,
    u.app_version,
    coalesce(o.orders, 0) > 0                           as reordered,
    coalesce(o.orders, 0)                               as orders,
    coalesce(o.gross_inr, 0)                            as gross_inr,
    coalesce(o.discount_inr, 0)                         as discount_inr,
    coalesce(o.gross_inr, 0) - coalesce(o.discount_inr, 0) as net_inr
from {{ ref('stg_experiment__users') }} u
left join orders o using (scenario, user_id)
