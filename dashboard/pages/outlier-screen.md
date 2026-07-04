---
title: Outlier screen
sidebar_position: 3
---

Same method as the case study, current quarter, live banks. So the language here is
deliberately boring. A high <abbr title="The average of six risk-signed z-scores. Higher means the bank's funding, growth, and balance-sheet mix sit further from its peer group, in the direction that history says to watch.">composite</abbr> means one thing: this bank's numbers sit
unusually far from its size group on six specific metrics. That's a reason to read
the bank profile page. It is not a prediction.

Method details: the metric map in the repository's `docs/backtest_method.md`,
lineage in [model docs](https://yugveerj.github.io/fdic-bank-health-monitor/dbt-docs/).

## How an analyst would use this

1. Pick your size band and sort by composite. The shortlist is the top handful,
   plus anything that moved sharply since the prior quarter.
2. For each name, read the per-metric columns: which of the six put it there,
   and is any of them sitting at the +5 cap, where saturation can inflate a
   score?
3. Open the bank's [profile page](/bank-profile) for trend context. A level, a
   trend, and one strange quarter are three different conversations.
4. Take what survives to primary sources: the call report, the filings, the
   footnotes. The screen's job ends where the reading begins.

```sql latest
select max(report_date) as latest_quarter from fdic.mart_outlier_flags
```

```sql bands
select distinct peer_band from fdic.mart_outlier_flags order by peer_band
```

<small>Scores below are for the quarter ended <Value data={latest} column=latest_quarter fmt='mmmm d, yyyy'/></small>

<Dropdown data={bands} name=band value=peer_band title="Size band" defaultValue="$1B-$10B"/>

```sql screen
select
    o.cert,
    b.bank_name,
    o.composite_score,
    o.n_screen_metrics,
    o.z_uninsured_share,
    o.z_brokered_share,
    o.z_securities_share,
    o.z_asset_growth_3y,
    o.z_nim_trend,
    o.z_equity_ratio,
    rank() over (order by o.composite_score desc) as band_rank,
    count(*) over () as band_size
from fdic.mart_outlier_flags o
join fdic.dim_banks b using (cert)
where o.report_date = (select latest_quarter from ${latest})
  and o.peer_band = '${inputs.band.value}'
  and b.is_active
order by o.composite_score desc
```

## Composite score distribution

```sql top_decile_line
select quantile_cont(composite_score, 0.9) as top_decile
from ${screen}
```

<Histogram data={screen} x=composite_score title="Composite scores — {inputs.band.value}, latest quarter">
    <ReferenceLine data={top_decile_line} x=top_decile label="top 10% of band" lineType=dashed/>
</Histogram>

## Ranked table with per-metric contributions

```sql screen_table
select * from ${screen} limit 50
```

<DataTable data={screen_table} rows=25>
    <Column id=band_rank title="Rank"/>
    <Column id=bank_name/>
    <Column id=cert title='FDIC cert' fmt='0'/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=n_screen_metrics title="Metrics"/>
    <Column id=z_uninsured_share title="Uninsured z" fmt='#,##0.0'/>
    <Column id=z_brokered_share title="Brokered z" fmt='#,##0.0'/>
    <Column id=z_securities_share title="Securities z" fmt='#,##0.0'/>
    <Column id=z_asset_growth_3y title="3y growth z" fmt='#,##0.0'/>
    <Column id=z_nim_trend title="NIM trend z" fmt='#,##0.0'/>
    <Column id=z_equity_ratio title="Equity z" fmt='#,##0.0'/>
</DataTable>

All six z-scores are risk-signed: positive always means further from peers in
the direction the screen watches. For equity, that means lower equity than the
peer group. Composites resting on fewer than six metrics (see the Metrics
column) carry more noise; the three-year growth metric in particular requires
twelve quarters of in-scope history.

## Biggest score increases since last quarter

A high composite is worth a look; a composite that *climbed* sharply in one
quarter is worth a look sooner. These are the banks in this band whose score rose
most between the last two quarters — a change in the funding, growth, or
balance-sheet mix the screen watches, not a verdict.

```sql movers
with q as (
    select distinct report_date from fdic.mart_outlier_flags order by 1 desc limit 2
),
latest_q as (select max(report_date) as d from q),
prior_q  as (select min(report_date) as d from q),
ranked_now as (
    select o.*, rank() over (order by o.composite_score desc) as band_rank,
           count(*) over () as band_size
    from fdic.mart_outlier_flags o
    join fdic.dim_banks b using (cert)
    where o.report_date = (select d from latest_q)
      and o.peer_band = '${inputs.band.value}'
      and b.is_active
)
select
    b.bank_name,
    o.cert,
    o.band_rank || ' of ' || o.band_size as rank_now,
    p.composite_score as prior_composite,
    o.composite_score as composite,
    o.composite_score - p.composite_score as change,
    case greatest(
        coalesce(o.z_uninsured_share - p.z_uninsured_share, -99),
        coalesce(o.z_brokered_share - p.z_brokered_share, -99),
        coalesce(o.z_securities_share - p.z_securities_share, -99),
        coalesce(o.z_asset_growth_3y - p.z_asset_growth_3y, -99),
        coalesce(o.z_nim_trend - p.z_nim_trend, -99),
        coalesce(o.z_equity_ratio - p.z_equity_ratio, -99))
      when o.z_uninsured_share - p.z_uninsured_share   then 'uninsured share'
      when o.z_brokered_share - p.z_brokered_share     then 'brokered share'
      when o.z_securities_share - p.z_securities_share then 'securities/assets'
      when o.z_asset_growth_3y - p.z_asset_growth_3y   then '3y growth'
      when o.z_nim_trend - p.z_nim_trend               then 'NIM trend'
      when o.z_equity_ratio - p.z_equity_ratio         then 'equity ratio'
    end as largest_metric_change
from ranked_now o
join fdic.dim_banks b using (cert)
join fdic.mart_outlier_flags p
      on p.cert = o.cert and p.report_date = (select d from prior_q)
where o.composite_score is not null
  and p.composite_score is not null
order by change desc
limit 12
```

<DataTable data={movers} rows=12>
    <Column id=bank_name title="Bank"/>
    <Column id=cert title='FDIC cert' fmt='0'/>
    <Column id=rank_now title="Rank now"/>
    <Column id=prior_composite title="Prior" fmt='#,##0.00'/>
    <Column id=composite title="Now" fmt='#,##0.00'/>
    <Column id=change title="Change" fmt='+#,##0.00;-#,##0.00' contentType=delta/>
    <Column id=largest_metric_change title="Largest metric change"/>
</DataTable>

## How the six metrics relate

The composite is an unweighted average of six risk-signed z-scores. That only
reads cleanly if the six aren't secretly saying the same thing. Below is how
correlated they are across every scored bank-quarter — values near zero mean the
metrics carry independent information; a high value would mean two of them
double-count. This is shown for honesty, not tuning: the composite stays
unweighted regardless of what it says. In the current data the largest pairwise
correlation is about 0.3 in magnitude; the six are close to independent.

```sql metric_corr
with z as (
    unpivot (
        select cert, report_date,
            z_uninsured_share, z_brokered_share, z_securities_share,
            z_asset_growth_3y, z_nim_trend, z_equity_ratio
        from fdic.mart_outlier_flags where composite_score is not null
    ) on z_uninsured_share, z_brokered_share, z_securities_share,
         z_asset_growth_3y, z_nim_trend, z_equity_ratio
    into name metric value z
),
labeled as (
    select cert, report_date, z,
        case metric
            when 'z_uninsured_share'  then 'Uninsured'
            when 'z_brokered_share'   then 'Brokered'
            when 'z_securities_share' then 'Securities'
            when 'z_asset_growth_3y'  then '3y growth'
            when 'z_nim_trend'        then 'NIM trend'
            when 'z_equity_ratio'     then 'Equity'
        end as metric
    from z
)
select a.metric as metric_a, b.metric as metric_b, round(corr(a.z, b.z), 2) as correlation
from labeled a
join labeled b on a.cert = b.cert and a.report_date = b.report_date
where a.metric <> b.metric
group by a.metric, b.metric
```

<Heatmap data={metric_corr} x=metric_a y=metric_b value=correlation valueFmt='#,##0.00' title="Correlation between the six screen metrics"/>

---

**Peer-relative statistics only. Nothing on this page is an assessment of any
bank's safety or soundness.**
