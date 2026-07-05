-- First- and last-touch columns re-attribute the SAME purchase sessions, so
-- their totals must match: purchases exactly, revenue to the cent (the two
-- rollups sum identical floats in different group orders). Divergence means
-- the channel join dropped or double-counted rows. Rows returned = failures.

select
    sum(first_touch_purchases)   as first_touch_total,
    sum(last_touch_purchases)    as last_touch_total,
    sum(first_touch_revenue_usd) as first_touch_revenue,
    sum(last_touch_revenue_usd)  as last_touch_revenue
from {{ ref('mart_ga4_sample_attribution') }}
having sum(first_touch_purchases) != sum(last_touch_purchases)
    or abs(sum(first_touch_revenue_usd) - sum(last_touch_revenue_usd)) > 0.01
