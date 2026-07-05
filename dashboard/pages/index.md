---
title: Bank Health Monitor
description: "Which banks look unusual next to their peers? Every FDIC-insured US bank over one billion in assets, scored against banks of similar size, updated automatically."
sidebar_position: 1
og:
  image: https://yugveerj.github.io/fdic-bank-health-monitor/og-image.png
---

Which banks look unusual next to their peers?

Every quarter this site pulls the financials of every FDIC-insured bank that has
crossed $1B in assets since 2019 and scores each one against banks of similar size.
The method gets tested on the only question that matters: would it have flagged the
banks that failed in 2023? Mostly, yes. One important miss. The case study covers both.

Everything updates itself. Weekly aggregates from the Federal Reserve, quarterly
filings from the FDIC, no hands on the wheel.

```sql build
select freshest_quarter, built_at, bank_quarters from fdic.build_meta
```

<small>Data through <Value data={build} column=freshest_quarter fmt='mmm yyyy'/> · <Value data={build} column=bank_quarters fmt='#,##0'/> bank-quarters · site rebuilt <Value data={build} column=built_at fmt='mmm d, yyyy'/></small>

## What the screen found

Frozen at June 2022, nine months before the first failure, the screen ranked
Silicon Valley Bank 1st of 35 in its size group and Signature Bank 2nd. First
Republic ranked 8th, a miss [the case study](/backtest-2023) spends real time
on. The data itself fought back too: federal failure records briefly labeled
Citibank as failed, which is why this pipeline
[tests its data](/data-quality).

## Where to go next

Start at the [peer-group explorer](/peer-explorer) to calibrate what normal looks
like inside each size band. Then the [outlier screen](/outlier-screen) ranks the
current quarter across three bands, and any name that catches your eye has its
full history on the [bank profile](/bank-profile). The same peer statistics are
also published as a
[Tableau Public satellite](https://public.tableau.com/app/profile/yugveer.jain/viz/FDICBankHealthMonitorPeerSatellite/Peerexplorer),
fed from the marts through a Google Sheet extract.

## The sector at a glance

```sql latest
select max(report_date) as latest_quarter from fdic.fct_bank_quarters
```

```sql kpis
with two_q as (
    select distinct report_date from fdic.fct_bank_quarters order by 1 desc limit 2
),
per_q as (
    select
        f.report_date,
        count(*) filter (b.is_active)                          as active_reporting,
        sum(total_assets)  filter (b.is_active) / 1e9          as sector_assets_t,
        median(roa_pct)                filter (b.is_active)    as median_roa,
        median(net_interest_margin_pct) filter (b.is_active)   as median_nim,
        median(equity_to_assets)       filter (b.is_active)    as median_equity_ratio
    from fdic.fct_bank_quarters f
    join fdic.dim_banks b using (cert)
    where f.report_date in (select report_date from two_q)
    group by f.report_date
)
select
    max_by(active_reporting, report_date)     as active_reporting,
    max_by(sector_assets_t, report_date)      as sector_assets_t,
    max_by(median_roa, report_date)           as median_roa,
    max_by(median_nim, report_date)           as median_nim,
    max_by(median_equity_ratio, report_date)  as median_equity_ratio,
    min_by(median_roa, report_date)           as prior_roa,
    min_by(median_nim, report_date)           as prior_nim,
    min_by(active_reporting, report_date)     as prior_reporting
from per_q
```

<BigValue data={kpis} value=active_reporting title="Active banks reporting (latest quarter)"/>
<BigValue data={kpis} value=sector_assets_t fmt='"$"#,##0.0"T"' title="Combined assets (active banks)"/>
<BigValue data={kpis} value=median_roa fmt='#,##0.00"%"' title="Median ROA"/>
<BigValue data={kpis} value=median_nim fmt='#,##0.00"%"' title="Median NIM"/>
<BigValue data={kpis} value=median_equity_ratio fmt='pct1' title="Median equity/assets"/>

<small>Prior quarter: <Value data={kpis} column=prior_reporting fmt='#,##0'/> active banks · median ROA <Value data={kpis} column=prior_roa fmt='#,##0.00'/>% · median NIM <Value data={kpis} column=prior_nim fmt='#,##0.00'/>%. Hover for definitions: <abbr title="Return on assets. What the bank earned as a share of everything it holds. Around 1% is normal for a healthy bank.">ROA</abbr> · <abbr title="Net interest margin. The gap between what a bank earns on its loans and what it pays on its deposits. For most banks, this is the engine.">NIM</abbr> · <abbr title="The bank's own capital as a share of its balance sheet. A thicker cushion means more room to absorb losses.">equity/assets</abbr></small>

## Sector balance sheet over time

The sum grows for two reasons at once: banks grow, and banks cross the $1B scope
bar into the panel. The right axis counts who is in the sum each quarter.

```sql sector_trend
select
    report_date,
    sum(total_assets) / 1e6   as "Total assets ($B)",
    sum(total_deposits) / 1e6 as "Total deposits ($B)",
    count(*)                  as "Banks in panel"
from fdic.fct_bank_quarters
group by report_date order by report_date
```

<LineChart data={sector_trend} x=report_date y={["Total assets ($B)", "Total deposits ($B)"]} y2="Banks in panel" yFmt='"$"#,##0"B"' y2Fmt='#,##0'/>

## Net interest margin, median bank by size band

Margins were squeezed hardest through 2022 and have been rebuilding since. The
largest banks run structurally thinner margins than the small-band median in
every quarter of the panel.

```sql band_trend
select report_date, peer_band,
       median(net_interest_margin_pct) as median_nim
from fdic.fct_bank_quarters
group by report_date, peer_band order by report_date
```

<LineChart data={band_trend} x=report_date y=median_nim series=peer_band yFmt='#,##0.0"%"'/>

## Funding mix, median bank

The metric the screen watches most closely: the median bank's estimated
uninsured share peaked just before the 2023 failures and has drifted lower
since, while brokered funding roughly doubled off its low.

```sql funding_trend
select report_date,
       median(uninsured_deposit_share) as "Uninsured share (est.)",
       median(brokered_deposit_share)  as "Brokered share"
from fdic.fct_bank_quarters
group by report_date order by report_date
```

<LineChart data={funding_trend} x=report_date y={["Uninsured share (est.)", "Brokered share"]} yFmt=pct1>
    <ReferenceLine x='2023-03-31' label="2023 failures" lineType=dashed/>
</LineChart>

## The weekly pulse (Federal Reserve H.8)

The weekly pulse comes from the Fed's H.8 release: deposits, bank credit, business
lending, and total assets across all US commercial banks. It's the freshest public
read on the sector between quarterly filings.

```sql h8
-- indexed so four series of very different size share one axis; try_cast keeps
-- this correct when the local build has no FRED data
with obs as (
    select try_cast(obs_date as date) as obs_date, series_title,
           try_cast(value_billions as double) as v
    from fdic.fred_h8
    where try_cast(obs_date as date) >= '2024-01-01'
)
select obs_date, series_title,
       v / first_value(v) over (partition by series_title order by obs_date) * 100 as indexed
from obs
where v is not null
order by obs_date
```

<LineChart data={h8} x=obs_date y=indexed series=series_title yFmt='#,##0' title="Indexed to the first 2024 week = 100"/>

## Twelve weeks ahead

A weekly forecast of the sector aggregates above — sector totals only, never
individual banks. Each series is forecast by whichever method survived a
rolling-origin backtest against a seasonal-naive baseline ("this year looks
like last year"); where nothing beat the baseline, the baseline is published
and the table below says so.

```sql fc_series_list
select distinct series_title from fdic.h8_forecasts order by 1
```

<Dropdown data={fc_series_list} name=fc_series value=series_title title="Series"/>

```sql fc_fan
-- six months of actuals, then the published 12-week path with its 95%
-- interval as separate bound lines
with recent as (
    select try_cast(obs_date as date) as week,
           try_cast(value_billions as double) as actual,
           cast(null as double) as forecast,
           cast(null as double) as lo_95,
           cast(null as double) as hi_95
    from fdic.fred_h8
    where series_title = '${inputs.fc_series.value}'
      and try_cast(obs_date as date) >= current_date - interval 180 day
),
path as (
    select try_cast(forecast_week as date) as week,
           cast(null as double) as actual,
           try_cast(forecast as double) as forecast,
           try_cast(lo_95 as double) as lo_95,
           try_cast(hi_95 as double) as hi_95
    from fdic.h8_forecasts
    where series_title = '${inputs.fc_series.value}'
)
select * from recent union all select * from path order by week
```

<LineChart data={fc_fan} x=week y={['actual','forecast','lo_95','hi_95']} yFmt='#,##0' title="Billions of dollars: actuals, published forecast, 95% interval"/>

```sql fc_backtest
select series_title,
       method,
       round(mape, 2)  as "MAPE %",
       round(smape, 2) as "sMAPE %",
       n_origins       as "backtest origins",
       case when published then 'published' else '' end as status
from fdic.h8_forecast_backtest
order by series_title, smape
```

<DataTable data={fc_backtest} rows=all title="Rolling-origin backtest — the published method has to earn it"/>

Backtest mechanics: expanding training window starting at two years of
weekly history, a new forecast origin every four weeks, twelve-week horizon,
errors pooled across all origins. Recomputed every Saturday after the H.8
release lands. These are statements about sector totals, not about any bank.

---

Peer-relative statistics from public filings, never an assessment of any
bank's condition.
