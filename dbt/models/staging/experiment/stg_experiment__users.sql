select
    scenario,
    user_id::bigint     as user_id,
    variant,
    app_version
from {{ source('experiment', 'ab_users') }}
