---
title: Peer-group explorer
---

Pick a <abbr title="Banks are only compared against banks of similar size: $1–10B, $10–100B, and over $100B in assets.">size band</abbr> and a metric. The page shows the full distribution and who sits in
the tails. It's worth a few minutes here before reading anyone's <abbr title="How far a bank sits from the middle of its size group, measured so that a few extreme banks can't distort the yardstick (median and MAD instead of mean and standard deviation). Zero is typical. Two is unusual. Scores are capped at plus or minus five.">z-score</abbr>, because
this is where you calibrate what normal looks like. Normal is wider than you think.

```sql latest
select max(report_date) as latest_quarter from fdic.fct_bank_quarters
```

```sql bands
select distinct peer_band from fdic.mart_peer_percentiles order by peer_band
```

```sql metrics
select distinct metric,
    case metric
        when 'uninsured_deposit_share'    then 'Uninsured deposit share'
        when 'brokered_deposit_share'     then 'Brokered deposit share'
        when 'securities_to_assets'       then 'Securities / assets'
        when 'asset_growth_3y_cagr'       then 'Asset growth (3-yr CAGR)'
        when 'asset_growth_yoy'           then 'Asset growth (YoY)'
        when 'deposit_growth_yoy'         then 'Deposit growth (YoY)'
        when 'nim_trend_4q'               then 'NIM trend (4-qtr slope)'
        when 'equity_to_assets'           then 'Equity / assets'
        when 'loans_to_deposits'          then 'Loans / deposits'
        when 'roa_pct'                    then 'Return on assets (%)'
        when 'noncurrent_loans_ratio_pct' then 'Noncurrent loans (%)'
        when 'net_chargeoffs_ratio_pct'   then 'Net charge-offs (%)'
        when 'cost_of_funds_pct'          then 'Cost of funds (%)'
        when 'efficiency_ratio_pct'       then 'Efficiency ratio (%)'
        else metric
    end as metric_label
from fdic.mart_peer_percentiles order by metric_label
```

<Dropdown data={bands} name=band value=peer_band title="Peer band" defaultValue="$1B-$10B"/>
<Dropdown data={metrics} name=metric value=metric label=metric_label title="Metric" defaultValue="roa_pct"/>

```sql selection
select p.cert, b.bank_name, p.value, p.robust_z
from fdic.mart_peer_percentiles p
join fdic.dim_banks b using (cert)
where p.report_date = (select latest_quarter from ${latest})
  and p.peer_band = '${inputs.band.value}'
  and p.metric = '${inputs.metric.value}'
  and b.is_active
```

```sql markers
select
    quantile_cont(value, 0.10) as p10,
    median(value)              as p50,
    quantile_cont(value, 0.90) as p90
from ${selection}
```

<Histogram data={selection} x=value title="Distribution of {inputs.metric.label} — {inputs.band.value}, latest quarter">
    <ReferenceLine data={markers} x=p10 label="10th" lineType=dashed color=#94a3b8/>
    <ReferenceLine data={markers} x=p50 label="median" color=#2563eb/>
    <ReferenceLine data={markers} x=p90 label="90th" lineType=dashed color=#94a3b8/>
</Histogram>

<DataTable data={markers}>
    <Column id=p10 title="10th percentile"/>
    <Column id=p50 title="Peer median"/>
    <Column id=p90 title="90th percentile"/>
</DataTable>

## Top and bottom deciles

```sql deciles
with ranked as (
    select *, percent_rank() over (order by value) as pr
    from ${selection}
    where value is not null
)
select bank_name, cert, '/bank-profile/' || cast(cert as integer) as profile_url,
       value, robust_z,
       case when pr >= 0.9 then 'Top decile' else 'Bottom decile' end as decile
from ranked
where pr >= 0.9 or pr <= 0.1
order by value desc
```

<DataTable data={deciles} rows=40>
    <Column id=profile_url contentType=link linkLabel=bank_name title="Bank"/>
    <Column id=cert/>
    <Column id=value/>
    <Column id=robust_z title="Robust z"/>
    <Column id=decile/>
</DataTable>

## Same metric, business-model peers

Size bands answer "unusual for a bank this big." This section answers "unusual
for a bank that runs this kind of business" — four rule-based groups from three
reported ratios: traditional lenders, wholesale-funded, securities-focused, and
fee-and-custody banks. The outlier screen's composite stays on size bands; this
view is context.

```sql models
select distinct business_model,
    case business_model
        when 'traditional_lender' then 'Traditional lender'
        when 'wholesale_funded'   then 'Wholesale-funded'
        when 'securities_focused' then 'Securities-focused'
        when 'fee_custody'        then 'Fee & custody'
        else business_model
    end as business_model_label
from fdic.mart_model_percentiles order by business_model_label
```

<Dropdown data={models} name=model value=business_model label=business_model_label title="Business model" defaultValue="traditional_lender"/>

```sql model_selection
select p.cert, b.bank_name, p.value, p.robust_z
from fdic.mart_model_percentiles p
join fdic.dim_banks b using (cert)
where p.report_date = (select latest_quarter from ${latest})
  and p.business_model = '${inputs.model.value}'
  and p.metric = '${inputs.metric.value}'
  and b.is_active
```

```sql model_metric_available
select count(*) as n from fdic.mart_model_percentiles
where metric = '${inputs.metric.value}'
```

{#if (model_metric_available[0]?.n ?? 0) > 0}

<Histogram data={model_selection} x=value title="Distribution of {inputs.metric.label} within {inputs.model.label}"/>

{:else}

The business-model groups are built from balance-sheet structure and return
ratios, so the year-over-year growth, net charge-off, and cost-of-funds metrics
aren't computed here — those stay on the size bands above. Pick another metric
to see its business-model distribution.

{/if}

---

High or low values here are statements about position in a distribution,
nothing more.
