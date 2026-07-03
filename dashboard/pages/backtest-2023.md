---
title: 2023 case study
---

<!-- TODO(revise): the backtest narrative is mine to write — this page currently
     shows the frozen data exhibit only. The reproducible backtest command,
     methodology narrative, false-positive analysis, and the full limitations
     discussion (including the metric-selection hindsight caveat and the
     amended-data caveat) publish with the backtest itself. -->

## Would this screen have flagged the 2023 bank failures?

This page freezes the composite screen at **2022-06-30** — using only report dates
on or before that quarter — and shows where the banks that failed in 2023 ranked
among their peers nine months earlier.

_Preliminary exhibit: the full reproducible backtest, methodology narrative, and
false-positive analysis are in progress. Two honesty notes apply to everything
below: the screen's metrics were chosen with knowledge of the 2023 events, and
the FDIC API serves current values, which may include amendments filed after
mid-2022 — this is a demonstration of screening methodology on historical data,
not an out-of-sample discovery._

```sql frozen
select
    o.cert,
    b.bank_name,
    o.peer_band,
    o.composite_score,
    o.n_screen_metrics,
    b.is_failed,
    b.failure_date,
    rank() over (partition by o.peer_band order by o.composite_score desc) as rank_in_band,
    count(*) over (partition by o.peer_band) as band_size
from fdic.mart_outlier_flags o
join fdic.dim_banks b using (cert)
where o.report_date = '2022-06-30'
```

```sql labeled
select bank_name, peer_band, composite_score, rank_in_band, band_size,
       case cert
           when 27330 then 'Voluntary liquidation (Mar 2023)'
           else 'Failed ' || strftime(failure_date, '%b %Y')
       end as outcome
from ${frozen}
where is_failed or cert = 27330
order by composite_score desc
```

<DataTable data={labeled}>
    <Column id=bank_name/>
    <Column id=outcome/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite (2022-Q2)" fmt='#,##0.00'/>
    <Column id=rank_in_band title="Rank in band"/>
    <Column id=band_size title="Band size"/>
</DataTable>

## The frozen 2022-Q2 distribution, all banks

```sql top_frozen
select bank_name, peer_band, composite_score, rank_in_band, band_size,
       case when is_failed then 'Failed in 2023' when cert = 27330 then 'Voluntarily liquidated' else '' end as note
from ${frozen}
where rank_in_band <= 10
order by peer_band, rank_in_band
```

<DataTable data={top_frozen} rows=30 groupBy=peer_band>
    <Column id=bank_name/>
    <Column id=rank_in_band title="Rank"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=note title="2023 outcome"/>
</DataTable>

### Scope notes, stated plainly

- **Heartland Tri-State Bank** (~$139M) and **Citizens Bank, Sac City** (~$66M)
  also failed in 2023. Both sat far below this project's $1B scope threshold in
  every quarter, so they are not in this data and the screen cannot see them.
- **Silvergate Bank** wound down voluntarily in March 2023 and therefore does not
  appear in the FDIC failures data; it is labeled separately above rather than
  silently mixed in.
- **Republic Bank (Philadelphia)** failed in April 2024 — after the 2023 events
  this case study is built around. It appears in the labeled table for
  completeness because it is in the failure data, not as part of the 2023 label
  set; at the 2022-Q2 freeze it ranked 86th of 826 in its band, and that result
  is reported as-is.
- Banks listed without a note are **currently operating institutions**; their
  position in a 2022 distribution is a peer-relative statistic from that quarter's
  filings — nothing more.

---

_Failure language on this page refers only to institutions that actually failed
or closed in 2023. For all operating banks: peer-relative statistics, not
assessments of safety or soundness._
