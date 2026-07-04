---
title: 2023 case study
sidebar_position: 5
description: Freeze the data at June 30, 2022 — where did the banks that failed in 2023 rank among their peers nine months earlier?
og:
  image: https://yugveerj.github.io/fdic-bank-health-monitor/og-image.png
---

## Would this screen have flagged the 2023 bank failures?

This page freezes the data at June 30, 2022 and asks where the banks that failed in
2023 ranked among their peers nine months earlier, using only what had been reported
by that date. 989 banks make the <abbr title="Only data reported on or before June 30, 2022. In other words, what an analyst could actually have seen nine months before the failures.">frozen</abbr> snapshot: 826 in the $1–10B band, 128 in
$10–100B, 35 above $100B.

Two things to keep in mind while reading. First, I picked these six metrics knowing
how 2023 ended. So this is a test of whether a simple peer screen can express a
known story in data that was available at the time. It is not a claim that I would
have called it in advance. Second, the FDIC's API serves current values, including
amendments filed after mid-2022, so the freeze is a close reconstruction of the
mid-2022 view rather than a perfect one.

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

```sql labeled_2023
select bank_name, peer_band, composite_score,
       rank_in_band || ' of ' || band_size as band_rank_display,
       band_pctile,
       case cert
           when 27330 then 'Liquidated Mar 2023'
           else 'Failed ' || strftime(failure_date, '%b %Y')
       end as outcome
from ${frozen}
where (is_failed and date_part('year', failure_date) = 2023) or cert = 27330
order by band_pctile desc
```

<DataTable data={labeled_2023}>
    <Column id=bank_name/>
    <Column id=outcome/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=band_rank_display title="Rank in band"/>
    <Column id=band_pctile title="Band pctile"/>
</DataTable>

**Read this first — two honesty notes that govern everything below.** The
screen's six metrics were chosen with knowledge of the 2023 events: this is a
demonstration of screening methodology on historical data, not an out-of-sample
discovery, and it claims no predictive validity. And the FDIC API serves current
values, which may include amendments filed after mid-2022 — the freeze
reconstructs the mid-2022 view approximately, not as a true point-in-time
vintage.


The screen works where the failure looked like the classic profile. Silicon Valley
Bank ranks first of 35 in the over-$100B band at the freeze, with a
<abbr title="The average of six risk-signed z-scores. Higher means the bank's funding, growth, and balance-sheet mix sit further from its peer group, in the direction that history says to watch.">composite</abbr> of
1.73. Signature ranks second at 1.45. Silvergate, which wound itself down
voluntarily in March 2023 rather than failing, ranks second of 128 in the $10–100B
band at 2.09. Three institutions that ended in 2023, all sitting at or near the top
of their peer groups nine months out, on public data alone.

First Republic is the honest miss. At the freeze it ranked 8th of 35 with a
composite of 0.61. Elevated, not alarming. The reason is instructive: my rate-risk
proxy is <abbr title="How much of the balance sheet sits in bonds. Safe in credit terms. In a fast rate-hiking cycle, painful in price terms.">securities as a share of assets</abbr>, and that's the SVB profile. First
Republic parked its rate risk somewhere these six metrics barely look, in long
fixed-rate jumbo mortgages, funded by wealthy clients whose balances sat far above
the insurance cap. The per-metric table below shows which components fired for it
and which stayed quiet. A screen that equal-weights six ratios doesn't get to catch
everything, and pretending otherwise would be worse than the miss.

```sql labeled_components
select o.bank_name,
       o.composite_score,
       f.z_uninsured_share, f.z_brokered_share, f.z_securities_share,
       f.z_asset_growth_3y, f.z_nim_trend, f.z_equity_ratio
from ${frozen} o
join fdic.mart_outlier_flags f
  on f.cert = o.cert and f.report_date = '2022-06-30'
where (o.is_failed and date_part('year', o.failure_date) = 2023) or o.cert = 27330
order by o.composite_score desc
```

<DataTable data={labeled_components}>
    <Column id=bank_name/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=z_uninsured_share title="Uninsured z" fmt='#,##0.0'/>
    <Column id=z_brokered_share title="Brokered z" fmt='#,##0.0'/>
    <Column id=z_securities_share title="Securities z" fmt='#,##0.0'/>
    <Column id=z_asset_growth_3y title="3y growth z" fmt='#,##0.0'/>
    <Column id=z_nim_trend title="NIM trend z" fmt='#,##0.0'/>
    <Column id=z_equity_ratio title="Equity z" fmt='#,##0.0'/>
</DataTable>

## What the screen's inputs looked like as 2022 approached

The labeled banks' raw screen ingredients, every quarter from 2019 to the
freeze. These are the trends the composite compressed into one number.

```sql labeled_trends
select f.report_date, b.bank_name,
       f.uninsured_deposit_share, f.securities_to_assets, f.asset_growth_3y_cagr,
       f.equity_to_assets, f.net_interest_margin_pct
from fdic.fct_bank_quarters f
join fdic.dim_banks b using (cert)
where f.cert in (24735, 57053, 59017, 27330)
  and f.report_date <= '2022-06-30'
order by f.report_date
```

<Grid cols=2>
<LineChart data={labeled_trends} x=report_date y=uninsured_deposit_share series=bank_name yFmt=pct0 title="Estimated uninsured-deposit share"/>
<LineChart data={labeled_trends} x=report_date y=securities_to_assets series=bank_name yFmt=pct0 title="Securities / assets"/>
<LineChart data={labeled_trends} x=report_date y=asset_growth_3y_cagr series=bank_name yFmt=pct0 title="Asset growth, 3-yr CAGR"/>
<LineChart data={labeled_trends} x=report_date y=equity_to_assets series=bank_name yFmt=pct1 title="Equity / assets"/>
<LineChart data={labeled_trends} x=report_date y=net_interest_margin_pct series=bank_name yFmt='#,##0.0"%"' title="Net interest margin"/>
</Grid>

## Where the labeled banks sat among all 989

989 composites at the freeze; the labeled institutions are marked.

```sql labeled_lines
select bank_name, composite_score from ${frozen}
where cert in (24735, 57053, 59017, 27330)
```

<Histogram data={frozen} x=composite_score title="All frozen composites, 2022-06-30">
    <ReferenceLine data={labeled_lines} x=composite_score label=bank_name labelPosition=aboveEnd/>
</Histogram>

## The top of each band at the freeze

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
- Banks listed without a note are **currently operating institutions**. Their
  position in a 2022 distribution is just that: a statistic from one quarter's
  filings.

## An out-of-window check: Republic First

One more failure gets a look, clearly separated from the 2023 set. Republic First
(it did business as Republic Bank, Philadelphia) failed in April 2024, ten months
past the window this page tests. At the freeze it sat 86th of 826 in its band with
a composite of 1.23. Top decile, nothing dramatic. I left it in because quietly
dropping the awkward case is exactly what a screen like this should never do.

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

What I'd actually claim for this method: it's a shortlist generator. Six ratios,
equal weights, no fitting. It hands an analyst a small stack of banks worth an
afternoon each, and in mid-2022 those afternoons would have been well spent. The
false-positive section below is the other half of that argument.

## The banks the screen flagged that didn't fail

A screen is only honest if you look at what it got wrong. Of the 100 banks in the
top decile of the frozen composite (at or above the 90th percentile of their size
band, ties included), 89 are still operating today; of the eleven that aren't,
three are the cases above and the rest were acquired, not failed. I looked closely
at five.

First Bank & Trust of Lubbock, Texas and SmartBank of Pigeon Forge, Tennessee are
growth artifacts. Both crossed the three-year growth threshold because they bought
other banks, not because hot deposits flooded in. Acquisition growth and SVB-style
organic growth look identical to a ratio and completely different to a human. The
merger flag on the data quality page exists because of these two.

Beal Bank USA of Las Vegas fired on brokered funding, securities, and margin
trend — the standing shape of a wholesale-funded specialty lender, worn with a
capital cushion so thick that its equity component scored safer than its peer
band.

Stifel Bank of Saint Louis has no acquisitions in the FDIC record for the window;
its flagged growth is sweep deposits arriving from its brokerage affiliate —
<abbr title="Deposits bought through middlemen instead of gathered from local customers. Cheap to scale up. Quick to leave.">brokered</abbr> by design, organic in the only sense a ratio can't see. Greene
County Commercial Bank of Catskill, New York holds municipal deposits —
<abbr title="The slice of deposits above the FDIC's $250,000 insurance cap. These are the dollars with a reason to run.">uninsured</abbr> on paper, collateralized in practice — parked in securities, so
the two metrics built to catch flighty money and rate risk both fired on a
business model designed around exactly those features.

The pattern across all five: the screen reads balance-sheet shape, and some
business models wear an unusual shape comfortably. That's why this is a shortlist,
not a verdict, and why the analyst reading the shortlist still matters.

```sql five_examined
select bank_name, peer_band, composite_score,
       rank_in_band || ' of ' || band_size as rank_display
from ${frozen}
where cert in (14778, 58463, 57833, 57358, 57710)
order by composite_score desc
```

The five, as the frozen screen saw them:

<DataTable data={five_examined}>
    <Column id=bank_name/>
    <Column id=peer_band title="Band"/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
    <Column id=rank_display title="Rank in band"/>
</DataTable>

### Top 10 of the flagged decile

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
    <Column id=merger_flagged title="Merger-flagged (2022-Q2)"/>
</DataTable>

The merger flag applies to the freeze quarter only; growth-window acquisitions
can sit in earlier quarters. One disambiguation: the Signature Bank in this
table (a $1B–$10B bank, FDIC cert 58264) is a different institution from the
failed New York Signature Bank.

What this page argues for is the method running today: the
[outlier screen](/outlier-screen) applies the same six metrics to the latest
quarter, and the [data-quality page](/data-quality) shows the tests behind the
numbers.

The exhibit reproduces from one command (`uv run python -m scripts.run_backtest`),
which rebuilds every model from data physically truncated at the freeze date and
proves the result matches this site's mart exactly — methodology and per-metric
rationale:
[backtest_method.md](https://github.com/yugveerj/fdic-bank-health-monitor/blob/main/docs/backtest_method.md).

---

_Failure language on this page refers only to institutions that actually failed
or closed. For all operating banks: peer-relative statistics, not assessments of
safety or soundness._
