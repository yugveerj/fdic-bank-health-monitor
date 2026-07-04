---
title: Bank profile
---

Twenty-nine quarters of any bank in the data, grouped into five metric families.
The story of a bank is usually in the trend, not the level.

```sql banks
select cert, bank_name || ' — ' || city || ', ' || state_code as label
from fdic.dim_banks
order by bank_name
```

<Dropdown data={banks} name=bank value=cert label=label title="Institution (closed banks included)" defaultValue={628}/>

```sql bank_history
select f.*, b.bank_name
from fdic.fct_bank_quarters f
join fdic.dim_banks b using (cert)
where f.cert = ${inputs.bank.value}
order by f.report_date
```

```sql profile_header
select bank_name, max(report_date) as latest, count(*) as quarters,
       max_by(business_model, report_date) as business_model
from ${bank_history} group by bank_name
```

<BigValue data={profile_header} value=bank_name title="Institution"/>
<BigValue data={profile_header} value=quarters title="Quarters reported"/>
<BigValue data={profile_header} value=business_model title="Business model (rule-based)"/>

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

## Profitability

```sql profitability
select report_date, roa_pct, roe_pct, net_interest_margin_pct, efficiency_ratio_pct
from ${bank_history} order by report_date
```

<LineChart data={profitability} x=report_date y={["roa_pct", "net_interest_margin_pct"]} yFmt='#,##0.00"%"' title="ROA and NIM"/>
<LineChart data={profitability} x=report_date y=efficiency_ratio_pct yFmt='#,##0"%"' title="Efficiency ratio"/>

## Capital

```sql capital
select report_date, equity_to_assets, cet1_ratio_pct / 100 as cet1_ratio, leverage_ratio_pct / 100 as leverage_ratio
from ${bank_history} order by report_date
```

<LineChart data={capital} x=report_date y={["equity_to_assets", "cet1_ratio", "leverage_ratio"]} yFmt=pct1/>

## Funding mix

```sql funding
select report_date, uninsured_deposit_share, brokered_deposit_share, loans_to_deposits
from ${bank_history} order by report_date
```

<LineChart data={funding} x=report_date y={["uninsured_deposit_share", "brokered_deposit_share"]} yFmt=pct1 title="Deposit composition"/>
<LineChart data={funding} x=report_date y=loans_to_deposits yFmt=pct0 title="Loans / deposits"/>

## Asset quality and growth

```sql quality
select report_date, noncurrent_loans_ratio_pct, net_chargeoffs_ratio_pct, asset_growth_yoy
from ${bank_history} order by report_date
```

<LineChart data={quality} x=report_date y={["noncurrent_loans_ratio_pct", "net_chargeoffs_ratio_pct"]} yFmt='#,##0.00"%"' title="Noncurrent loans and net charge-offs"/>
<LineChart data={quality} x=report_date y=asset_growth_yoy yFmt=pct0 title="Asset growth, year over year"/>

---

Filings as reported to the FDIC; nothing here judges any institution.
