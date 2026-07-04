---
title: Outlier screen
---

Same method as the case study, current quarter, live banks. So the language here is
deliberately boring. A high <abbr title="The average of six risk-signed z-scores. Higher means the bank's funding, growth, and balance-sheet mix sit further from its peer group, in the direction that history says to watch.">composite</abbr> means one thing: this bank's numbers sit
unusually far from its size group on six specific metrics. That's a reason to read
the bank profile page. It is not a prediction.

Method details: the metric map in the repository's `docs/backtest_method.md`,
lineage in [model docs](https://yugveerj.github.io/fdic-bank-health-monitor/dbt-docs/).

```sql latest
select max(report_date) as latest_quarter from fdic.mart_outlier_flags
```

```sql bands
select distinct peer_band from fdic.mart_outlier_flags order by peer_band
```

<Dropdown data={bands} name=band value=peer_band title="Peer band" defaultValue="$1B-$10B"/>

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
    o.z_equity_ratio
from fdic.mart_outlier_flags o
join fdic.dim_banks b using (cert)
where o.report_date = (select latest_quarter from ${latest})
  and o.peer_band = '${inputs.band.value}'
  and b.is_active
order by o.composite_score desc
```

## Composite score distribution

<Histogram data={screen} x=composite_score title="Composite scores — {inputs.band.value}, latest quarter"/>

## Ranked table with per-metric contributions

```sql screen_table
select * from ${screen} limit 50
```

<DataTable data={screen_table} rows=25>
    <Column id=bank_name/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=n_screen_metrics title="Metrics"/>
    <Column id=z_uninsured_share title="Uninsured z" fmt='#,##0.0'/>
    <Column id=z_brokered_share title="Brokered z" fmt='#,##0.0'/>
    <Column id=z_securities_share title="Securities z" fmt='#,##0.0'/>
    <Column id=z_asset_growth_3y title="3y growth z" fmt='#,##0.0'/>
    <Column id=z_nim_trend title="NIM trend z" fmt='#,##0.0'/>
    <Column id=z_equity_ratio title="Equity z" fmt='#,##0.0'/>
</DataTable>

Composites resting on fewer than six metrics (see the Metrics column) carry more
noise; the three-year growth metric in particular requires twelve quarters of
in-scope history.

## How an analyst would use this

1. Pick your size band and sort by composite. The shortlist is the top handful,
   plus anything that moved sharply since the prior quarter.
2. For each name, read the per-metric columns: which of the six put it there,
   and is any of them sitting at the +5 cap, where saturation can inflate a
   score?
3. Open the bank's profile page for trend context. A level, a trend, and one
   strange quarter are three different conversations.
4. Take what survives to primary sources: the call report, the filings, the
   footnotes. The screen's job ends where the reading begins.

---

**Peer-relative statistics only. Nothing on this page is an assessment of any
bank's safety or soundness.**
