with totals as (
    select 'All channels' as channel, sum(impressions) as impressions, sum(clicks) as clicks, sum(conversions) as conversions
    from {{ ref('stg_blinkit__marketing_performance') }}
    union all
    select channel, sum(impressions), sum(clicks), sum(conversions)
    from {{ ref('stg_blinkit__marketing_performance') }}
    group by channel
),

stages as (
    select channel, 1 as stage_order, 'Impressions' as stage, impressions as volume, impressions as top from totals
    union all
    select channel, 2, 'Clicks', clicks, impressions from totals
    union all
    select channel, 3, 'Conversions', conversions, impressions from totals
)

select
    channel,
    stage_order,
    stage,
    volume,
    round(volume::numeric / top, 4)                                                             as share_of_top,
    round(volume::numeric / lag(volume) over (partition by channel order by stage_order), 4)    as share_of_previous
from stages
