---
title: Bank profile
sidebar_position: 4
---

Twenty-nine quarters of any bank in the data, grouped into five metric families.
The story of a bank is usually in the trend, not the level.

```sql banks
select cert, bank_name || ' — ' || city || ', ' || state_code as label
from fdic.dim_banks
order by bank_name
```

<Dropdown data={banks} name=bank value=cert label=label title="Institution (closed banks included)" defaultValue={24735}/>

```sql bank_history
select f.*, b.bank_name
from fdic.fct_bank_quarters f
join fdic.dim_banks b using (cert)
where f.cert = ${inputs.bank.value}
order by f.report_date
```

```sql profile_header
select bank_name, max(report_date) as latest, count(*) as quarters,
       case max_by(business_model, report_date)
           when 'traditional_lender' then 'Traditional lender'
           when 'wholesale_funded'   then 'Wholesale-funded'
           when 'securities_focused' then 'Securities-focused'
           when 'fee_custody'        then 'Fee & custody'
           else max_by(business_model, report_date)
       end as business_model,
       max_by(peer_band, report_date) as peer_band
from ${bank_history} group by bank_name
```

<BigValue data={profile_header} value=bank_name title="Institution"/>
<BigValue data={profile_header} value=quarters title="Quarters reported"/>
<BigValue data={profile_header} value=peer_band title="Size band (latest)"/>
<BigValue data={profile_header} value=business_model title="Business model"/>

```sql screen_history
select report_date, composite_score, n_screen_metrics
from fdic.mart_outlier_flags
where cert = ${inputs.bank.value}
order by report_date
```

<LineChart data={screen_history} x=report_date y=composite_score yFmt='#,##0.00' title="Composite score vs size peers, by quarter">
    <ReferenceLine y=0 label="peer-typical"/>
</LineChart>

Positive means the bank sat further from its size peers in the direction the
screen watches, scored within whichever size band it belonged to that quarter. A
blank stretch is a quarter with too few of the six metrics to score.

```sql screen_now
with bank_latest as (
    select max(report_date) as d from fdic.mart_outlier_flags
    where cert = ${inputs.bank.value}
),
flags as (
    select * from fdic.mart_outlier_flags
    where cert = ${inputs.bank.value}
      and report_date = (select d from bank_latest)
),
pct as (
    select metric, value, peer_median
    from fdic.mart_peer_percentiles
    where cert = ${inputs.bank.value}
      and report_date = (select d from bank_latest)
)
select
    case p.metric
        when 'uninsured_deposit_share' then 'Uninsured deposit share'
        when 'brokered_deposit_share'  then 'Brokered deposit share'
        when 'securities_to_assets'    then 'Securities / assets'
        when 'asset_growth_3y_cagr'    then 'Asset growth (3-yr CAGR)'
        when 'nim_trend_4q'            then 'NIM trend (4-qtr slope)'
        when 'equity_to_assets'        then 'Equity / assets'
    end as metric_label,
    case when p.metric = 'nim_trend_4q'
         then printf('%.2f pp/qtr', p.value)
         else printf('%.1f%%', p.value * 100) end as bank_value,
    case when p.metric = 'nim_trend_4q'
         then printf('%.2f pp/qtr', p.peer_median)
         else printf('%.1f%%', p.peer_median * 100) end as band_median,
    case p.metric
        when 'uninsured_deposit_share' then f.z_uninsured_share
        when 'brokered_deposit_share'  then f.z_brokered_share
        when 'securities_to_assets'    then f.z_securities_share
        when 'asset_growth_3y_cagr'    then f.z_asset_growth_3y
        when 'nim_trend_4q'            then f.z_nim_trend
        when 'equity_to_assets'        then f.z_equity_ratio
    end as risk_signed_z,
    case p.metric
        when 'uninsured_deposit_share' then 'Funding mix'
        when 'brokered_deposit_share'  then 'Funding mix'
        when 'securities_to_assets'    then 'Balance sheet'
        when 'asset_growth_3y_cagr'    then 'Asset quality and growth'
        when 'nim_trend_4q'            then 'Profitability'
        when 'equity_to_assets'        then 'Capital'
    end as shown_under
from pct p
cross join flags f
where p.metric in ('uninsured_deposit_share','brokered_deposit_share',
    'securities_to_assets','asset_growth_3y_cagr','nim_trend_4q','equity_to_assets')
order by abs(risk_signed_z) desc nulls last
```

{#if screen_now.length > 0}

The six metrics the screen scores, this bank against its size band in its
latest scored quarter. Positive z always points the direction the screen
watches.

<DataTable data={screen_now}>
    <Column id=metric_label title="Screen metric"/>
    <Column id=bank_value title="This bank"/>
    <Column id=band_median title="Band median"/>
    <Column id=risk_signed_z title="Risk-signed z" fmt='#,##0.0'/>
    <Column id=shown_under title="Trend shown under"/>
</DataTable>

{/if}

## Balance sheet

```sql balance
select report_date,
       total_assets / 1e6   as "Assets ($B)",
       total_deposits / 1e6 as "Deposits ($B)",
       net_loans_leases / 1e6 as "Net loans ($B)",
       securities / 1e6     as "Securities ($B)"
from ${bank_history} order by report_date
```

<LineChart data={balance} x=report_date y={["Assets ($B)", "Deposits ($B)", "Net loans ($B)", "Securities ($B)"]} yFmt='"$"#,##0.0"B"'/>

```sql sec_share
select report_date, securities_to_assets as "Securities / assets"
from ${bank_history} order by report_date
```

<LineChart data={sec_share} x=report_date y="Securities / assets" yFmt=pct0 title="Securities as a share of assets"/>

## Profitability

```sql profitability
select report_date,
       roa_pct                 as "Return on assets (%)",
       net_interest_margin_pct as "Net interest margin (%)",
       efficiency_ratio_pct    as "Efficiency ratio (%)"
from ${bank_history} order by report_date
```

<LineChart data={profitability} x=report_date y={["Return on assets (%)", "Net interest margin (%)"]} yFmt='#,##0.00"%"' title="ROA and NIM"/>
<LineChart data={profitability} x=report_date y="Efficiency ratio (%)" yFmt='#,##0"%"' title="Efficiency ratio"/>

## Capital

```sql capital
select report_date,
       equity_to_assets     as "Equity / assets",
       cet1_ratio_pct / 100 as "CET1 ratio",
       leverage_ratio_pct / 100 as "Leverage ratio"
from ${bank_history} order by report_date
```

<LineChart data={capital} x=report_date y={["Equity / assets", "CET1 ratio", "Leverage ratio"]} yFmt=pct1/>

## Funding mix

```sql funding
select report_date,
       uninsured_deposit_share as "Uninsured share (est.)",
       brokered_deposit_share  as "Brokered share",
       loans_to_deposits       as "Loans / deposits"
from ${bank_history} order by report_date
```

<LineChart data={funding} x=report_date y={["Uninsured share (est.)", "Brokered share"]} yFmt=pct1 title="Deposit composition"/>
<LineChart data={funding} x=report_date y="Loans / deposits" yFmt=pct0 title="Loans / deposits"/>

## Asset quality and growth

```sql quality
select report_date,
       noncurrent_loans_ratio_pct as "Noncurrent loans (%)",
       net_chargeoffs_ratio_pct   as "Net charge-offs (%)",
       asset_growth_yoy           as "Asset growth (1y)",
       asset_growth_3y_cagr       as "Asset growth (3y CAGR)"
from ${bank_history} order by report_date
```

<LineChart data={quality} x=report_date y={["Noncurrent loans (%)", "Net charge-offs (%)"]} yFmt='#,##0.00"%"' title="Noncurrent loans and net charge-offs"/>
<LineChart data={quality} x=report_date y={["Asset growth (1y)", "Asset growth (3y CAGR)"]} yFmt=pct0 title="Asset growth, one and three year"/>

---

Filings as reported to the FDIC; nothing here judges any institution.
