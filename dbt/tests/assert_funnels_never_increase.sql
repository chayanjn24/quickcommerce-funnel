select 'marketing' as funnel, channel as segment, stage
from {{ ref('campaign_funnel_stages') }}
where share_of_previous > 1
union all
select 'amazon', segment, stage
from {{ ref('amazon_funnel') }}
where share_of_previous > 1
union all
select 'marketing row', campaign_id::text, 'clicks > impressions or conversions > clicks'
from {{ ref('stg_blinkit__marketing_performance') }}
where clicks > impressions or conversions > clicks
