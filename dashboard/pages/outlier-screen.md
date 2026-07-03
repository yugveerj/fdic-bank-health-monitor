---
title: Outlier screen
---

<!-- TODO(revise): framing paragraph in my words — what this screen is and is not. -->

Each currently active bank's composite score is the mean of six risk-signed,
peer-relative robust z-scores (funding mix, securities exposure, growth, margin
trend, capital). Positive means further from the peer median in the directions
the screen watches. Method details: the metric map in the repository's
`docs/backtest_method.md`, lineage in [model docs](https://yugveerj.github.io/fdic-bank-health-monitor/dbt-docs/).

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

---

**Peer-relative statistics, not assessments of safety or soundness.** A high
composite score means a bank's reported ratios sit far from its peer-group median
in the screen's chosen directions — a statistical statement about public filings,
not a prediction, rating, or supervisory judgment of any kind.
