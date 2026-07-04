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
select distinct metric from fdic.mart_peer_percentiles order by metric
```

<Dropdown data={bands} name=band value=peer_band title="Peer band" defaultValue="$1B-$10B"/>
<Dropdown data={metrics} name=metric value=metric title="Metric" defaultValue="roa_pct"/>

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

<Histogram data={selection} x=value title="Distribution of {inputs.metric.value} — {inputs.band.value}, latest quarter"/>

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
select bank_name, cert, value, robust_z,
       case when pr >= 0.9 then 'Top decile' else 'Bottom decile' end as decile
from ranked
where pr >= 0.9 or pr <= 0.1
order by value desc
```

<DataTable data={deciles} rows=40>
    <Column id=bank_name/>
    <Column id=cert/>
    <Column id=value/>
    <Column id=robust_z title="Robust z"/>
    <Column id=decile/>
</DataTable>

---

High or low values here are statements about position in a distribution,
nothing more.
