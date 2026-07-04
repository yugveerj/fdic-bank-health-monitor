---
title: 2023 case study
---

<!-- TODO(revise): the interpretive narrative on this page is mine — the exhibits
     are generated, the words about them should be in my voice and defensible. -->

## Would this screen have flagged the 2023 bank failures?

This page freezes the composite screen at **2022-06-30** and shows where the
banks at the center of the 2023 banking stress ranked among their peers nine
months earlier. The entire exhibit reproduces from one command
(`uv run python -m scripts.run_backtest`), which rebuilds every model from data
physically truncated at the freeze date and proves the result matches this
site's mart exactly — methodology and per-metric rationale:
[backtest_method.md](https://github.com/yugveerj/fdic-bank-health-monitor/blob/main/docs/backtest_method.md).

**Read this first — two honesty notes that govern everything below.** The
screen's six metrics were chosen with knowledge of the 2023 events: this is a
demonstration of screening methodology on historical data, not an out-of-sample
discovery, and it claims no predictive validity. And the FDIC API serves current
values, which may include amendments filed after mid-2022 — the freeze
reconstructs the mid-2022 view approximately, not as a true point-in-time
vintage.

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
    count(*) over (partition by o.peer_band) as band_size,
    round(percent_rank() over (partition by o.peer_band order by o.composite_score) * 100, 1) as band_pctile,
    rank() over (order by o.composite_score desc) as rank_overall,
    count(*) over () as n_overall,
    round(percent_rank() over (order by o.composite_score) * 100, 1) as overall_pctile
from fdic.mart_outlier_flags o
join fdic.dim_banks b using (cert)
where o.report_date = '2022-06-30'
```

## The 2023 events

The label set is the three 2023 failures large enough for this project's $1B
scope, plus Silvergate's voluntary liquidation, labeled separately because it
does not appear in FDIC failure data. With only four labeled events, results
are presented as ranks and distribution positions — capture rates or lift
statistics would be meaningless at this n.

```sql labeled_2023
select bank_name, peer_band, composite_score,
       rank_in_band || ' of ' || band_size as band_rank_display,
       band_pctile,
       rank_overall || ' of ' || n_overall as overall_rank_display,
       case cert
           when 27330 then 'Liquidated Mar 2023'
           else 'Failed ' || strftime(failure_date, '%b %Y')
       end as outcome
from ${frozen}
where (is_failed and date_part('year', failure_date) = 2023) or cert = 27330
order by composite_score desc
```

<DataTable data={labeled_2023}>
    <Column id=bank_name/>
    <Column id=outcome/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=band_rank_display title="Rank in band"/>
    <Column id=band_pctile title="Band pctile"/>
    <Column id=overall_rank_display title="Rank overall"/>
</DataTable>

<!-- TODO(revise): my read of this table, including the honest sentence about
     First Republic sitting at the 79th percentile of its band — what the six
     metrics structurally could and couldn't see about it. -->

## What the screen's inputs looked like as 2022 approached

The labeled banks' raw screen ingredients, every quarter from 2019 to the
freeze. These are the trends the composite compressed into one number.

```sql labeled_trends
select f.report_date, b.bank_name,
       f.uninsured_deposit_share, f.securities_to_assets,
       f.equity_to_assets, f.net_interest_margin_pct, f.brokered_deposit_share
from fdic.fct_bank_quarters f
join fdic.dim_banks b using (cert)
where f.cert in (24735, 57053, 59017, 27330)
  and f.report_date <= '2022-06-30'
order by f.report_date
```

<LineChart data={labeled_trends} x=report_date y=uninsured_deposit_share series=bank_name yFmt=pct0 title="Estimated uninsured-deposit share"/>
<LineChart data={labeled_trends} x=report_date y=securities_to_assets series=bank_name yFmt=pct0 title="Securities / assets"/>
<LineChart data={labeled_trends} x=report_date y=equity_to_assets series=bank_name yFmt=pct1 title="Equity / assets"/>
<LineChart data={labeled_trends} x=report_date y=net_interest_margin_pct series=bank_name yFmt='#,##0.0"%"' title="Net interest margin"/>

## The frozen 2022-Q2 distribution, all banks

```sql top_frozen
select bank_name, peer_band, composite_score,
       rank_in_band || ' of ' || band_size as rank_display,
       case when is_failed and date_part('year', failure_date) = 2023 then 'Failed in 2023'
            when cert = 27330 then 'Voluntarily liquidated'
            else '' end as note
from ${frozen}
where rank_in_band <= 10
order by peer_band, rank_in_band
```

<DataTable data={top_frozen} rows=30 groupBy=peer_band>
    <Column id=bank_name/>
    <Column id=rank_display title="Rank"/>
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
- Banks listed without a note are **currently operating institutions**; their
  position in a 2022 distribution is a peer-relative statistic from that quarter's
  filings — nothing more.

## The top decile that didn't fail

A screen that only surfaced future failures would be suspicious; this one's top
decile is mostly banks that went on to be fine, and looking at *why they scored
high* is part of honest methodology. Recurring shapes: brokered-deposit z-scores
pinned at the +5 winsorization boundary (a documented saturation on
zero-inflated metrics), composites resting on four or five of the six metrics,
and acquisition-driven growth — the merger flag below separates step-change
growth from the organic deposit-inflow kind. One disambiguation: the Signature
Bank appearing here (cert 58264, a $1B–$10B bank) is a different institution
from the failed New York Signature Bank.

```sql false_positives
select o.cert, o.bank_name, o.peer_band, o.composite_score, o.n_screen_metrics,
       o.rank_in_band || ' of ' || o.band_size as rank_display,
       coalesce(f.likely_merger_quarter, false) as merger_flagged
from ${frozen} o
left join fdic.fct_bank_quarters f
       on f.cert = o.cert and f.report_date = '2022-06-30'
where o.band_pctile >= 90
  and o.cert not in (24735, 57053, 59017, 27330, 27332)
order by o.composite_score desc
limit 10
```

<DataTable data={false_positives}>
    <Column id=bank_name/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=n_screen_metrics title="Metrics"/>
    <Column id=rank_display title="Rank"/>
    <Column id=merger_flagged title="Merger-flagged"/>
</DataTable>

<!-- TODO(revise): my written analysis of ~5 of these banks — what the screen
     saw, why it didn't translate into failure, and which of them are
     saturation artifacts versus genuinely unusual funding models. -->

## Out-of-window check: Republic Bank (April 2024)

One in-scope bank failed *after* the 2023 window this case study is built
around: Republic Bank of Philadelphia (FDIC cert 27332, $5.9B at failure,
April 2024). It is not part of the label set — the screen was assembled around
the 2023 events — but pretending it doesn't exist would be curation, so its
frozen-quarter result is reported here as-is: at 2022-06-30 the composite placed
it at the 89.7th percentile of its band, just outside the top decile. Whatever
that says about the screen's reach beyond its design window belongs in the
limitations discussion, not in a quiet omission.

```sql republic
select bank_name, peer_band, composite_score,
       rank_in_band || ' of ' || band_size as band_rank_display,
       band_pctile,
       'Failed ' || strftime(failure_date, '%b %Y') as outcome
from ${frozen}
where cert = 27332
```

<DataTable data={republic}>
    <Column id=bank_name/>
    <Column id=outcome/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=band_rank_display title="Rank in band"/>
    <Column id=band_pctile title="Band pctile"/>
</DataTable>

---

_Failure language on this page refers only to institutions that actually failed
or closed. For all operating banks: peer-relative statistics, not assessments of
safety or soundness._
