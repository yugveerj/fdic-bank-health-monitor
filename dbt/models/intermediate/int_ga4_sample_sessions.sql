-- One row per session. Events without a ga_session_id carry no session context
-- and are dropped here.
--
-- Two channel labels, because GA4 exports two different signals:
--   session_channel     — session-scoped source/medium from event params; often
--                         null in the export, so nulls collapse to the GA-style
--                         '(direct) / (none)' bucket
--   first_touch_channel — the user-scoped traffic_source struct, i.e. how the
--                         user was FIRST acquired, identical across all of a
--                         user's sessions

with events as (
    select * from {{ ref('stg_ga4_sample__events') }}
    where ga_session_id is not null
)

select
    session_key,
    user_pseudo_id,
    ga_session_id,
    max(ga_session_number)                            as ga_session_number,
    min(event_date)                                   as session_date,
    min(event_ts)                                     as session_start_ts,
    max(ga_session_number) = 1                        as is_first_session,
    max(session_engaged) = 1                          as engaged,
    any_value(device_category)                        as device_category,
    any_value(country)                                as country,
    countif(event_name = 'page_view')                 as pageviews,
    countif(event_name = 'view_item')                 as items_viewed,
    countif(event_name = 'add_to_cart')               as carts,
    countif(event_name = 'begin_checkout')            as checkouts,
    countif(event_name = 'purchase')                  as purchases,
    sum(purchase_revenue_usd)                         as revenue_usd,
    concat(
        coalesce(array_agg(event_source ignore nulls order by event_ts limit 1)[safe_offset(0)], '(direct)'),
        ' / ',
        coalesce(array_agg(event_medium ignore nulls order by event_ts limit 1)[safe_offset(0)], '(none)')
    )                                                 as session_channel,
    concat(
        coalesce(any_value(first_touch_source), '(direct)'),
        ' / ',
        coalesce(any_value(first_touch_medium), '(none)')
    )                                                 as first_touch_channel
from events
group by session_key, user_pseudo_id, ga_session_id
