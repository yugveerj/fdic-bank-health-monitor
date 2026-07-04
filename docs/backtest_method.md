# Backtest methodology

<!-- TODO(revise): this document is written to be defensible line by line — I own
     every sentence of it and should be able to reproduce the reasoning cold. -->

## The question

Would a peer-relative outlier screen, built on FDIC public data and frozen to
what was reportable at 2022-06-30, have flagged the banks at the center of the
2023 banking stress? This is a methodology demonstration on historical data —
see the limitations, which are load-bearing.

## The freeze, and its proof

One command reproduces everything: `uv run python -m scripts.run_backtest`.

It rebuilds the entire model pipeline in a separate database from raw financials
physically truncated at the as-of date (belt: the staging model also takes an
`as_of` variable; braces: the raw copy simply doesn't contain later rows), then
asserts that the frozen build's composite scores are **identical** to the
production mart's rows at that date — 989 of 989 banks. That equivalence is the
point: it demonstrates that every screen metric is computed only from
backward-looking data, so the "as-of" view is real, not aspirational.

## Metric sources

Every field code below comes from the FDIC's official dictionaries (saved under
`docs/fdic_*_properties.yaml`) and was confirmed against a live `/financials`
response on 2026-07-03. Dollar levels are thousands; ratio fields are percent.

| Metric | Source field(s) | Notes |
|---|---|---|
| Total assets | `ASSET` | |
| Total deposits | `DEP` | |
| Net loans & leases | `LNLSNET` | |
| Loans / deposits | derived: `LNLSNET / DEP` | computed in dbt |
| ROA | `ROA` | |
| ROE | `ROE` | |
| Net interest margin | `NIMY` | 4-quarter trend slope computed in dbt |
| Efficiency ratio | `EEFFR` | |
| Noninterest income share | `NONIIR` (+ `NONII` level) | |
| Equity / assets | `EQR` (+ `EQ` level) | |
| Risk-based capital | `RBCRWAJ` (total), `RBCT1CER` (CET1), `RBC1AAJ` (leverage) | |
| Brokered-deposit share | derived: `BRO / DEP` | `BRO` is the level, thousands |
| Uninsured-deposit share | derived: `DEPUNINS / DEP` | FDIC's own estimate; `DEPUNA` (domestic-offices variant) also ingested |
| Cost of funds | `INTEXPY` | interest expense / earning assets |
| Noncurrent loans ratio | `NCLNLSR` (+ `NCLNLS` level) | |
| Net charge-offs ratio | `NTLNLSCOR` (+ `NTLNLS` level) | `NTLNLS` is year-to-date |
| Nonperforming assets / assets | `NPERFV` | |
| Securities / assets | derived: `SC / ASSET` | |
| YoY / 3-yr asset growth | derived from `ASSET` | quarter-index joins in dbt |
| YoY deposit growth | derived from `DEP` | computed in dbt |

## Screen metrics and risk directions

Six metrics, fixed before the backtest was built and not adjusted afterward —
wherever a labeled bank lands, that is what gets reported. `+` means a higher
value scores as riskier.

| Metric | Direction | One-sentence rationale |
|---|---|---|
| Uninsured-deposit share | + | Deposits above the insurance limit are the ones that can leave in an afternoon, so a funding base dominated by them is structurally runnable. |
| Brokered-deposit share | + | Brokered money is rate-shopping money — it arrives for yield and leaves for yield, with no relationship holding it in place. |
| Securities / assets | + | In a rising-rate environment a large securities book is embedded duration: unrealized losses that turn real exactly when deposits need paying out — the "aren't securities safe?" answer is *not when rates just rose and you must sell them*. |
| 3-yr asset growth | + | Balance sheets that tripled in three years have risk controls, funding relationships, and asset quality that were built for a much smaller bank. |
| NIM 4-quarter trend | − | A margin that is deteriorating quarter after quarter means the bank is being squeezed between its asset yields and its funding costs. |
| Equity / assets | − | Capital is the distance between a bad quarter and insolvency; less of it means less room for anything to go wrong. |

**Composite** = mean of the available risk-signed robust z-scores
(`(value − peer_median) / (1.4826 × MAD)`, winsorized at ±5, MAD = 0 → null),
computed within the quarter's asset band ($1–10B, $10–100B, >$100B).
`n_screen_metrics` records how many of the six fed each composite.

The spec allowed considering an unrealized-loss/AOCI field as a seventh metric;
I did not pursue it — the metric set was frozen before results were examined,
and it stays frozen.

## Labels

- **2023 label set**: Silicon Valley Bank (24735), Signature Bank NY (57053),
  First Republic Bank (59017) — the three 2023 failures above the $1B scope —
  plus Silvergate Bank (27330), a voluntary liquidation absent from FDIC failure
  data by design, labeled separately.
- **Excluded, stated openly**: Heartland Tri-State (~$139M) and Citizens Bank,
  Sac City (~$66M) failed in 2023 far below the scope threshold; the screen
  never sees them.
- **Out-of-window**: Republic Bank, Philadelphia (27332) failed in April 2024.
  Not part of the label set; its freeze-date result is reported as-is as a
  robustness observation.

## Results at the 2022-06-30 freeze

| Bank | Band | Rank in band | Band pctile | Overall (n=989) | Overall pctile |
|---|---|---|---|---|---|
| Silvergate Bank | $10B–$100B | 2 / 128 | 99.2 | 8 | 99.3 |
| Silicon Valley Bank | >$100B | 1 / 35 | 100.0 | 26 | 97.5 |
| Signature Bank | >$100B | 2 / 35 | 97.1 | 60 | 94.0 |
| First Republic Bank | >$100B | 8 / 35 | 79.4 | 355 | 64.2 |
| Republic Bank (2024, out-of-window) | $1B–$10B | 86 / 826 | 89.7 | 95 | 90.5 |

With only 3–4 labeled events, these are presented as ranks and distribution
positions; capture-rate or lift statistics would be meaningless at this n and
are deliberately absent.

<!-- TODO(revise): the interpretation of these numbers — especially First
     Republic's weak in-band signal and what the screen structurally cannot see
     about it — is my analysis to write. -->

## False positives

`docs/backtest/false_positive_sample.csv` holds the top-decile banks that did
not fail. Recurring shapes in the sample: brokered-share z pinned at +5 (the
winsorization saturation documented in the README), composites resting on 4 of
6 metrics, and acquisition-driven growth (`likely_merger_quarter` flags in the
full ranked table separate step-change growth from organic SVB-style deposit
inflows). One disambiguation: the sample contains a *different* Signature Bank
(cert 58264, $1B–$10B) than the failed New York institution (57053).

<!-- TODO(revise): the written false-positive analysis — what the screen saw in
     ~5 of these banks and why they didn't fail — is mine. -->

## Limitations (load-bearing — these appear wherever results do)

1. **The screen was designed with hindsight.** The six metrics were chosen
   knowing how 2023 unfolded. This backtest demonstrates that a plausible
   screening methodology *would have ranked* these banks highly; it is not an
   out-of-sample discovery and cannot claim predictive validity.
2. **The freeze is approximate.** The FDIC API serves current values, which may
   include amendments filed after mid-2022. The as-of filter reconstructs the
   mid-2022 view from today's data — a true point-in-time vintage would require
   archived submissions I don't have.
3. **Winsorization saturates zero-inflated metrics** (brokered share above all):
   sixteen percent of brokered-share observations share the +5 boundary, which
   flattens distinctions among the most extreme banks and inflates their
   composites' similarity.
4. **The 3-year growth metric excludes recent scope-entrants** (it needs 12
   quarters of >$1B history), so roughly half of 2022-Q2 composites rest on
   five metrics, not six.
