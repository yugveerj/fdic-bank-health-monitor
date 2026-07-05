-- The same purchase sessions attributed two ways: last-touch = the purchase
-- session's own channel, first-touch = the purchasing user's original
-- acquisition channel. Totals are conserved across both columns (data test
-- asserts it); the interesting output is the gap between them per channel.
-- Full outer join because a channel can acquire buyers without closing any,
-- and vice versa; zeros where a side is absent.

with purchase_sessions as (
    select session_channel, first_touch_channel, purchases, revenue_usd
    from {{ ref('int_ga4_sample_sessions') }}
    where purchases > 0
),

first_touch as (
    select
        first_touch_channel   as channel,
        sum(purchases)        as first_touch_purchases,
        sum(revenue_usd)      as first_touch_revenue_usd
    from purchase_sessions
    group by first_touch_channel
),

last_touch as (
    select
        session_channel       as channel,
        sum(purchases)        as last_touch_purchases,
        sum(revenue_usd)      as last_touch_revenue_usd
    from purchase_sessions
    group by session_channel
)

select
    channel,
    coalesce(f.first_touch_purchases, 0)   as first_touch_purchases,
    coalesce(l.last_touch_purchases, 0)    as last_touch_purchases,
    coalesce(f.first_touch_revenue_usd, 0) as first_touch_revenue_usd,
    coalesce(l.last_touch_revenue_usd, 0)  as last_touch_revenue_usd
from first_touch f
full outer join last_touch l using (channel)
