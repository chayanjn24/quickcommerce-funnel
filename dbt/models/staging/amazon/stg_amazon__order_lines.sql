-- 7 order lines appear twice in the file; keep the one with the higher qty
with source as (
    select
        *,
        row_number() over (
            partition by order_id, sku
            order by qty::int desc, index::int
        ) as line_rank
    from {{ source('amazon', 'amazon_sale_report') }}
),

state_map as (
    select * from {{ ref('amazon_state_map') }}
)

select
    s.order_id,
    s.sku,
    to_date(s.date, 'MM-DD-YY')                         as ordered_on,
    s.status,
    s.fulfilment,
    s.ship_service_level,
    s.sales_channel,
    s.style,
    initcap(s.category)                                 as category,
    s.size,
    nullif(s.courier_status, '')                        as courier_status,
    s.qty::int                                          as qty,
    nullif(s.amount, '')::numeric(12, 2)                as amount_inr,
    upper(trim(s.ship_city))                            as ship_city,
    coalesce(m.state, nullif(upper(trim(s.ship_state)), ''), 'UNKNOWN') as ship_state,
    nullif(s.promotion_ids, '') is not null             as has_promotion,
    s.b2b::boolean                                      as is_b2b
from source s
left join state_map m on upper(trim(s.ship_state)) = m.raw_state
where s.line_rank = 1
