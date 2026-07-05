-- Channel rollup on the SESSION-scoped channel label. The export's
-- session-scoped source/medium params are sparse, so '(direct) / (none)' is
-- overweighted here — first-touch attribution lives in
-- mart_ga4_sample_attribution, not this table.

with sessions as (
    select * from {{ ref('int_ga4_sample_sessions') }}
)

select
    session_channel                                   as channel,
    count(*)                                          as sessions,
    count(distinct user_pseudo_id)                    as users,
    sum(purchases)                                    as purchases,
    coalesce(sum(revenue_usd), 0)                     as revenue_usd,
    safe_divide(countif(purchases > 0), count(*))     as purchase_cvr,
    count(*) / sum(count(*)) over ()                  as session_share
from sessions
group by session_channel
