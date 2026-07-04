---
title: US Bank Health Monitor
---

<!-- TODO(revise): one plain-English takeaway sentence per chart, mine. -->

Quarterly financials for every FDIC-insured bank that reported over $1B in total
assets in any quarter since 2019 — ingested from the FDIC's public API, modeled
and tested with dbt, rebuilt automatically on refresh.

```sql latest
select max(report_date) as latest_quarter from fdic.fct_bank_quarters
```

```sql kpis
select
    count(*)                                as banks_reporting,
    sum(total_assets) / 1e9                 as sector_assets_t,
    sum(total_deposits) / 1e9               as sector_deposits_t,
    median(roa_pct)                         as median_roa,
    median(net_interest_margin_pct)         as median_nim,
    median(equity_to_assets)                as median_equity_ratio
from fdic.fct_bank_quarters
where report_date = (select latest_quarter from ${latest})
```

<BigValue data={kpis} value=banks_reporting title="Banks > $1B reporting"/>
<BigValue data={kpis} value=sector_assets_t fmt='"$"#,##0.0"T"' title="Combined assets"/>
<BigValue data={kpis} value=median_roa fmt='#,##0.00"%"' title="Median ROA"/>
<BigValue data={kpis} value=median_nim fmt='#,##0.00"%"' title="Median NIM"/>
<BigValue data={kpis} value=median_equity_ratio fmt='pct1' title="Median equity/assets"/>

## Sector balance sheet over time

```sql sector_trend
select
    report_date,
    sum(total_assets) / 1e6   as "Total assets ($B)",
    sum(total_deposits) / 1e6 as "Total deposits ($B)"
from fdic.fct_bank_quarters
group by report_date order by report_date
```

<LineChart data={sector_trend} x=report_date y={["Total assets ($B)", "Total deposits ($B)"]} yFmt='"$"#,##0"B"'/>

<!-- TODO(revise): takeaway -->

## Profitability and margin, median bank by peer band

```sql band_trend
select report_date, peer_band,
       median(net_interest_margin_pct) as median_nim
from fdic.fct_bank_quarters
group by report_date, peer_band order by report_date
```

<LineChart data={band_trend} x=report_date y=median_nim series=peer_band yFmt='#,##0.0"%"' title="Median net interest margin by peer band"/>

<!-- TODO(revise): takeaway -->

## Funding mix, median bank

```sql funding_trend
select report_date,
       median(uninsured_deposit_share) as "Uninsured share (est.)",
       median(brokered_deposit_share)  as "Brokered share"
from fdic.fct_bank_quarters
group by report_date order by report_date
```

<LineChart data={funding_trend} x=report_date y={["Uninsured share (est.)", "Brokered share"]} yFmt=pct1/>

<!-- TODO(revise): takeaway -->

## The weekly pulse (Federal Reserve H.8)

Between quarterly filings, these system-wide weekly aggregates are the freshest
signal available — seasonally adjusted, in billions.

```sql h8
select obs_date, series_title, value_billions
from fdic.fred_h8
where obs_date >= '2024-01-01'
order by obs_date
```

<LineChart data={h8} x=obs_date y=value_billions series=series_title yFmt='"$"#,##0"B"'/>

<!-- TODO(revise): takeaway -->

---

_All figures are peer-relative statistical descriptions of public regulatory
filings — not assessments of any institution's safety or soundness._
