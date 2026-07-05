-- Weekly view -> cart -> purchase funnel, counted over whole sessions. Closed
-- funnel: a session is "in" a stage if it fired that stage's event OR any
-- deeper one — the sample's shards before 2020-11-16 carry almost no
-- add_to_cart events while purchases still occur, so open per-stage countifs
-- would break stage nesting. A deeper event is taken as proof the session
-- passed through (begin_checkout implies a cart existed). Stage rates are
-- conditional on the prior stage; overall_cvr is purchase over all sessions.
-- Edge weeks extend past the sample window's boundaries — kept, the dashboard
-- labels the window.

with sessions as (
    select * from {{ ref('int_ga4_sample_sessions') }}
),

staged as (
    select
        date_trunc(session_date, week(monday))                        as week,
        items_viewed > 0 or carts > 0 or checkouts > 0 or purchases > 0 as reached_view,
        carts > 0 or checkouts > 0 or purchases > 0                     as reached_cart,
        purchases > 0                                                   as reached_purchase
    from sessions
)

select
    week,
    count(*)                                          as sessions,
    countif(reached_view)                             as sessions_with_view,
    countif(reached_cart)                             as sessions_with_cart,
    countif(reached_purchase)                         as sessions_with_purchase,
    safe_divide(countif(reached_view), count(*))      as view_rate,
    safe_divide(countif(reached_cart), countif(reached_view))         as cart_rate_of_views,
    safe_divide(countif(reached_purchase), countif(reached_cart))     as purchase_rate_of_carts,
    safe_divide(countif(reached_purchase), count(*))  as overall_cvr
from staged
group by week
