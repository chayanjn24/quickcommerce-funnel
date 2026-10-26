-- the file's roas column doesn't match revenue / spend, so it's recalculated in campaign_funnel
select
    campaign_id::bigint                     as campaign_id,
    campaign_name,
    date::date                              as campaign_date,
    target_audience,
    channel,
    impressions::int                        as impressions,
    clicks::int                             as clicks,
    conversions::int                        as conversions,
    spend::numeric(12, 2)                   as spend,
    revenue_generated::numeric(12, 2)       as revenue,
    roas::numeric(8, 2)                     as roas_reported
from {{ source('blinkit', 'blinkit_marketing_performance') }}
