with o as (select * from {{ ref('fct_orders') }}),

slices as (
    select 'Month' as dimension, to_char(ordered_at, 'YYYY-MM') as value, * from o
    union all
    select 'Distance', distance_band, * from o
    union all
    select 'Hour of day', lpad(order_hour::text, 2, '0') || ':00', * from o
    union all
    select 'Weekday', order_weekday, * from o
    union all
    select 'Category', category, * from o
    union all
    select 'Promised window', promised_window_minutes::text || ' min', * from o
)

select
    dimension,
    value,
    count(*)                                                    as orders,
    round(avg((delivery_status = 'On Time')::int), 4)           as on_time_rate,
    round(avg((delivery_status = 'Significantly Delayed')::int), 4) as badly_late_rate,
    round(avg(minutes_vs_promise), 2)                           as avg_minutes_vs_promise,
    round(avg(rating), 2)                                       as avg_rating,
    round(avg((sentiment = 'Negative')::int), 4)                as negative_share
from slices
group by 1, 2
