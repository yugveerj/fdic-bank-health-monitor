-- Daily traffic and commerce topline, session-grain inputs. A session counts
-- toward the day it started. purchase_cvr is the share of sessions with at
-- least one purchase event, not purchases/sessions.

with sessions as (
    select * from {{ ref('int_ga4_sample_sessions') }}
)

select
    session_date                                      as date,
    count(*)                                          as sessions,
    countif(engaged)                                  as engaged_sessions,
    count(distinct user_pseudo_id)                    as users,
    count(distinct if(is_first_session, user_pseudo_id, null)) as new_users,
    sum(pageviews)                                    as pageviews,
    sum(purchases)                                    as purchases,
    coalesce(sum(revenue_usd), 0)                     as revenue_usd,
    safe_divide(countif(purchases > 0), count(*))     as purchase_cvr
from sessions
group by session_date
