---
title: Bank Health Monitor
description: "Which banks look unusual next to their peers? Every FDIC-insured US bank over one billion in assets, scored against banks of similar size, updated automatically."
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

## What the screen found

Frozen at June 2022, nine months before the first failure, the screen ranked
Silicon Valley Bank 1st of 35 in its size group and Signature Bank 2nd. First
Republic ranked 8th, a miss [the case study](/backtest-2023) spends real time
on. The data itself fought back too: federal failure records briefly labeled
Citibank as failed, which is why this pipeline
[tests its data](/data-quality).

```sql latest
select max(report_date) as latest_quarter from fdic.fct_bank_quarters
```

```sql kpis
select
    count(*)                                as banks_reporting,
    count(*) filter (b.is_active)           as active_reporting,
    sum(total_assets) / 1e9                 as sector_assets_t,
    sum(total_deposits) / 1e9               as sector_deposits_t,
    median(roa_pct)               filter (b.is_active) as median_roa,
    median(net_interest_margin_pct) filter (b.is_active) as median_nim,
    median(equity_to_assets)       filter (b.is_active) as median_equity_ratio
from fdic.fct_bank_quarters f
join fdic.dim_banks b using (cert)
where report_date = (select latest_quarter from ${latest})
```

<BigValue data={kpis} value=active_reporting title="Active banks reporting (latest quarter)"/>
<BigValue data={kpis} value=sector_assets_t fmt='"$"#,##0.0"T"' title="Combined assets"/>
<BigValue data={kpis} value=median_roa fmt='#,##0.00"%"' title="Median ROA"/>
<BigValue data={kpis} value=median_nim fmt='#,##0.00"%"' title="Median NIM"/>
<BigValue data={kpis} value=median_equity_ratio fmt='pct1' title="Median equity/assets"/>

<small>Hover for definitions: <abbr title="Return on assets. What the bank earned as a share of everything it holds. Around 1% is normal for a healthy bank.">ROA</abbr> · <abbr title="Net interest margin. The gap between what a bank earns on its loans and what it pays on its deposits. For most banks, this is the engine.">NIM</abbr> · <abbr title="The bank's own capital as a share of its balance sheet. A thicker cushion means more room to absorb losses.">equity/assets</abbr></small>

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


## Profitability and margin, median bank by peer band

```sql band_trend
select report_date, peer_band,
       median(net_interest_margin_pct) as median_nim
from fdic.fct_bank_quarters
group by report_date, peer_band order by report_date
```

<LineChart data={band_trend} x=report_date y=median_nim series=peer_band yFmt='#,##0.0"%"' title="Median net interest margin by peer band"/>


## Funding mix, median bank

```sql funding_trend
select report_date,
       median(uninsured_deposit_share) as "Uninsured share (est.)",
       median(brokered_deposit_share)  as "Brokered share"
from fdic.fct_bank_quarters
group by report_date order by report_date
```

<LineChart data={funding_trend} x=report_date y={["Uninsured share (est.)", "Brokered share"]} yFmt=pct1/>


## The weekly pulse (Federal Reserve H.8)

The weekly pulse comes from the Fed's H.8 release: deposits, bank credit, business
lending, and total assets across all US commercial banks. It's the freshest public
read on the sector between quarterly filings.

```sql h8
-- try_cast: with no local FRED key the extraction ships a single all-null row
-- whose parquet types degrade; casting keeps this correct in both worlds
select try_cast(obs_date as date) as obs_date, series_title,
       try_cast(value_billions as double) as value_billions
from fdic.fred_h8
where try_cast(obs_date as date) >= '2024-01-01'
order by 1
```

<LineChart data={h8} x=obs_date y=value_billions series=series_title yFmt='"$"#,##0"B"'/>


---

Peer-relative statistics from public filings, never an assessment of any
bank's condition.
