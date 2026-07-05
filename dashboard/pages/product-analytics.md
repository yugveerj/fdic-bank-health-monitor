---
title: Product analytics
sidebar_position: 7
---

<Alert status=warning>
<b>None of this is this site's traffic.</b> Every number on this page comes from
Google's obfuscated GA4 ecommerce sample — the Google Merchandise Store,
November 2020 through January 2021. It exists to exercise the GA4 staging
models and marts end to end before the site's own analytics property (Phase E)
starts exporting to BigQuery.
</Alert>

The pipeline is the point: raw GA4 export rows through a shared normalizing
macro, one row per session, then the marts feeding this page. The sample
property is a store, so the funnel below is view → cart → purchase; the site's
own funnel will look different, the plumbing won't. The sample is also
obfuscated — Google resamples users and thins events — so read shapes, not
levels.

## Daily traffic

```sql ga4_totals
select
    sum(sessions)    as sessions,
    sum(purchases)   as purchases,
    sum(revenue_usd) as revenue_usd,
    -- purchase_cvr is share-of-sessions per day; weight by sessions to get the
    -- window-level share (purchases/sessions would count repeat purchases twice)
    sum(purchase_cvr * sessions) / sum(sessions) as overall_cvr
from fdic.ga4_daily
```

<BigValue data={ga4_totals} value=sessions fmt='#,##0' title="Sessions"/>
<BigValue data={ga4_totals} value=purchases fmt='#,##0' title="Purchases"/>
<BigValue data={ga4_totals} value=revenue_usd fmt='"$"#,##0' title="Revenue"/>
<BigValue data={ga4_totals} value=overall_cvr fmt='pct2' title="Session CVR"/>

```sql ga4_daily_trend
select date, sessions, revenue_usd
from fdic.ga4_daily
order by date
```

<LineChart data={ga4_daily_trend} x=date y=sessions yFmt='#,##0' title="Sessions per day"/>

<AreaChart data={ga4_daily_trend} x=date y=revenue_usd yFmt='"$"#,##0' title="Purchase revenue per day"/>

## Weekly funnel

The funnel is closed: a session counts toward a stage if it fired that stage's
event or any deeper one. That matters on this sample — its earliest weeks
contain purchases but almost no `add_to_cart` events, so an open count would
show carts below purchases. The bars are the stage counts per week; the table
carries the rates between stages.

```sql funnel_stages
-- stage labels are numbered because the legend sorts alphabetically
with stages as (
    unpivot (
        select week,
               sessions_with_view     as "1. viewed an item",
               sessions_with_cart     as "2. added to cart",
               sessions_with_purchase as "3. purchased"
        from fdic.ga4_funnel
    ) on "1. viewed an item", "2. added to cart", "3. purchased"
    into name stage value sessions
)
select * from stages order by week, stage
```

<BarChart data={funnel_stages} x=week y=sessions series=stage type=grouped yFmt='#,##0' title="Sessions reaching each funnel stage, by week"/>

```sql funnel_rates
select week, sessions, view_rate, cart_rate_of_views, purchase_rate_of_carts, overall_cvr
from fdic.ga4_funnel
order by week
```

<DataTable data={funnel_rates} rows=all>
    <Column id=week title="Week of" fmt='mmm d, yyyy'/>
    <Column id=sessions title="Sessions" fmt='#,##0'/>
    <Column id=view_rate title="View rate" fmt=pct1/>
    <Column id=cart_rate_of_views title="Cart rate (of views)" fmt=pct1/>
    <Column id=purchase_rate_of_carts title="Purchase rate (of carts)" fmt=pct1/>
    <Column id=overall_cvr title="Overall CVR" fmt=pct2/>
</DataTable>

## Weekly retention cohorts

Users grouped by the week of their first session; each column is the share of
the cohort active again N weeks later. Week 0 is 100% by construction. The
sample window is only thirteen weeks, so late cohorts run out of runway.

```sql retention_grid
-- a blank cell is a week the sample window never reached, not zero retention
select
    cohort_week,
    any_value(cohort_size) as cohort_size,
    max(retention_pct) filter (week_number = 0)  as w0,
    max(retention_pct) filter (week_number = 1)  as w1,
    max(retention_pct) filter (week_number = 2)  as w2,
    max(retention_pct) filter (week_number = 3)  as w3,
    max(retention_pct) filter (week_number = 4)  as w4,
    max(retention_pct) filter (week_number = 5)  as w5,
    max(retention_pct) filter (week_number = 6)  as w6,
    max(retention_pct) filter (week_number = 7)  as w7,
    max(retention_pct) filter (week_number = 8)  as w8,
    max(retention_pct) filter (week_number = 9)  as w9,
    max(retention_pct) filter (week_number = 10) as w10,
    max(retention_pct) filter (week_number = 11) as w11,
    max(retention_pct) filter (week_number = 12) as w12
from fdic.ga4_retention
group by cohort_week
order by cohort_week
```

<DataTable data={retention_grid} rows=all>
    <Column id=cohort_week title="Cohort" fmt='mmm d, yyyy'/>
    <Column id=cohort_size title="Users" fmt='#,##0'/>
    <Column id=w0 title="W0" fmt=pct0 contentType=colorscale/>
    <Column id=w1 title="W1" fmt=pct0 contentType=colorscale/>
    <Column id=w2 title="W2" fmt=pct0 contentType=colorscale/>
    <Column id=w3 title="W3" fmt=pct0 contentType=colorscale/>
    <Column id=w4 title="W4" fmt=pct0 contentType=colorscale/>
    <Column id=w5 title="W5" fmt=pct0 contentType=colorscale/>
    <Column id=w6 title="W6" fmt=pct0 contentType=colorscale/>
    <Column id=w7 title="W7" fmt=pct0 contentType=colorscale/>
    <Column id=w8 title="W8" fmt=pct0 contentType=colorscale/>
    <Column id=w9 title="W9" fmt=pct0 contentType=colorscale/>
    <Column id=w10 title="W10" fmt=pct0 contentType=colorscale/>
    <Column id=w11 title="W11" fmt=pct0 contentType=colorscale/>
    <Column id=w12 title="W12" fmt=pct0 contentType=colorscale/>
</DataTable>

## Channels

Session-scoped source / medium. Sessions with no source params land in
`(direct) / (none)`, and in the raw export that bucket is bigger than the GA4
UI shows — the UI reassigns many direct sessions during processing; this table
doesn't.

```sql channels
select channel, sessions, session_share, users, purchases, purchase_cvr, revenue_usd
from fdic.ga4_channels
order by sessions desc
```

<DataTable data={channels} rows=15>
    <Column id=channel title="Channel"/>
    <Column id=sessions title="Sessions" fmt='#,##0'/>
    <Column id=session_share title="Share" fmt=pct1/>
    <Column id=users title="Users" fmt='#,##0'/>
    <Column id=purchases title="Purchases" fmt='#,##0'/>
    <Column id=purchase_cvr title="CVR" fmt=pct2/>
    <Column id=revenue_usd title="Revenue" fmt='"$"#,##0'/>
</DataTable>

## First touch vs last touch

The same purchase sessions, credited two ways. They disagree because they
measure different things: GA4's `traffic_source` struct is user-scoped — it
records what first acquired the user and repeats that on every later event, so
it can only ever say first touch. Last touch comes from the session-scoped
source / medium event params. A user acquired through google / organic who
comes back directly and buys is a google / organic purchase on one bar and a
`(direct) / (none)` purchase on the other. Neither is wrong, and total
purchases are identical between the two by construction.

```sql attribution_long
with p as (
    unpivot (
        select channel,
               first_touch_purchases as "first touch",
               last_touch_purchases  as "last touch"
        from fdic.ga4_attribution
    ) on "first touch", "last touch"
    into name model value purchases
)
-- the mart full-outer-joins the two rollups, so channels with zero purchases
-- under both models exist; they add nothing here
select * from p
qualify sum(purchases) over (partition by channel) > 0
order by purchases desc
```

<BarChart data={attribution_long} x=channel y=purchases series=model type=grouped swapXY=true yFmt='#,##0' title="Purchases credited per channel, two ways"/>

```sql attribution_table
select channel, first_touch_purchases, last_touch_purchases,
       first_touch_revenue_usd, last_touch_revenue_usd
from fdic.ga4_attribution
where first_touch_purchases + last_touch_purchases > 0
order by last_touch_purchases desc
```

<DataTable data={attribution_table} rows=all>
    <Column id=channel title="Channel"/>
    <Column id=first_touch_purchases title="First-touch purchases" fmt='#,##0'/>
    <Column id=last_touch_purchases title="Last-touch purchases" fmt='#,##0'/>
    <Column id=first_touch_revenue_usd title="First-touch revenue" fmt='"$"#,##0'/>
    <Column id=last_touch_revenue_usd title="Last-touch revenue" fmt='"$"#,##0'/>
</DataTable>

## The experiment

A powered experiment write-up on the same sample — power analysis first, then
the test — ships in the repository as
[docs/experiment_sample.md](https://github.com/yugveerj/fdic-bank-health-monitor/blob/main/docs/experiment_sample.md).
The numbers live there and aren't duplicated here.

---

**Sample data throughout — Google's obfuscated GA4 ecommerce dataset, not this
site's traffic.**
