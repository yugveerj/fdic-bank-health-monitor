# Backtest methodology

## The question

Would a peer-relative outlier screen, built on nothing but FDIC public data and
frozen to what was reportable at June 30, 2022, have flagged the banks at the
center of the 2023 banking stress? That's nine months before the first of them
failed. This document explains how the test works, where every number comes
from, and what the result does and does not mean. The short version of that
last part: the metrics were chosen knowing how 2023 ended, so this demonstrates
a screening method on history rather than discovering anything. The
limitations section expands on what that means for reading the results.

## Reproducing the June 2022 snapshot

Everything reproduces from a single command:

    uv run python -m scripts.run_backtest

The command rebuilds the entire model pipeline in a separate database whose raw
financials are physically truncated at the as-of date. As a second layer, the
staging model takes an `as_of` variable that filters in-model, so even if the
copy step regressed the models would still exclude later data.

The script then asserts that the frozen build's composite scores are identical
to the production mart's rows at that date, all 989 banks. Every screen metric
is built from trailing windows, so a mismatch here would indicate that one or
more of those window calculations depended on observations after the as-of
date. Matching exactly is the leakage check.

Two further assertions run after the equivalence. The script pins the labeled
banks to their published ranks, which guards against a subtler failure where
both sides of the equivalence drift together. And a fixture-scale version of
the whole rebuild runs on every pull request, with its own pinned rank.

## Where the data comes from

Every field code below comes from the FDIC's official data dictionaries, which
are saved under `docs/` as `fdic_*_properties.yaml`, and each code was
confirmed against a live API response before first use. Dollar-denominated
fields arrive in thousands. Ratio fields are percentages. Two fields that look
quarterly are actually year-to-date (net income and net charge-offs), which
matters if you ever de-cumulate them.

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
| Uninsured-deposit share | derived: `DEPUNINS / DEP` | the FDIC's own estimate; `DEPUNA` (domestic-offices variant) also ingested |
| Cost of funds | `INTEXPY` | interest expense / earning assets |
| Noncurrent loans ratio | `NCLNLSR` (+ `NCLNLS` level) | |
| Net charge-offs ratio | `NTLNLSCOR` (+ `NTLNLS` level) | `NTLNLS` is year-to-date |
| Nonperforming assets / assets | `NPERFV` | |
| Securities / assets | derived: `SC / ASSET` | |
| YoY / 3-yr asset growth | derived from `ASSET` | quarter-index joins in dbt |
| YoY deposit growth | derived from `DEP` | computed in dbt |

## The screen

Six metrics, fixed before the backtest was built and never adjusted afterward.
Wherever a labeled bank lands is what gets reported. Each metric carries a
direction: a plus means a higher value scores as riskier.

| Metric | Direction | Why |
|---|---|---|
| Uninsured-deposit share | + | Deposits above the insurance limit are the ones that can leave in an afternoon, so a funding base dominated by them is structurally runnable. |
| Brokered-deposit share | + | Brokered deposits arrive for yield and leave for yield, with no customer relationship holding them in place. |
| Securities / assets | + | In a rising-rate environment a large securities book is embedded duration: unrealized losses that turn real exactly when deposits need paying out. |
| 3-yr asset growth | + | A balance sheet that tripled in three years has risk controls, funding relationships, and asset quality that were built for a much smaller bank. |
| NIM 4-quarter trend | − | A margin deteriorating quarter after quarter means the bank is being squeezed between its asset yields and its funding costs. |
| Equity / assets | − | Less capital means less room to absorb losses before a bad quarter threatens solvency. |

Each metric is turned into a robust z-score within the bank's size band for
that quarter: the value minus the band median, divided by 1.4826 times the
median absolute deviation, winsorized at plus or minus five, and set to null
when the MAD is zero rather than dividing by it. Median and MAD instead of mean
and standard deviation because bank ratios have heavy tails, and a single
extreme peer shouldn't be able to mask or manufacture outliers. The bands are
one-to-ten billion, ten-to-a-hundred billion, and over a hundred billion in
assets, recomputed each quarter.

The composite is the unweighted mean of whichever risk-signed z-scores are
available for that bank-quarter, with a companion column recording how many of
the six fed it. Unweighted is a deliberate choice: three or four labeled
events are too few to estimate or validate metric weights. The specification
allowed considering an unrealized-loss field as a seventh metric; I didn't
pursue it, because the set was frozen before results were examined and it
stays frozen.

## The labels

The 2023 label set is the three failures large enough for the one-billion
scope, Silicon Valley Bank (24735), Signature Bank of New York (57053), and
First Republic Bank (59017), plus Silvergate Bank (27330), which wound down
voluntarily in March 2023 and therefore never appears in FDIC failure data. It
gets labeled separately rather than silently mixed in. Two 2023 failures fall
far below scope, Heartland Tri-State at roughly $139M and Citizens Bank of Sac
City at roughly $66M; the case-study page says so instead of dropping them
quietly. Republic First of Philadelphia (27332) failed in April 2024, ten
months outside the window, and is reported as an out-of-window check rather
than as part of the label set.

## The result

At the June 2022 freeze, against 989 scored banks:

| Bank | Band | Rank in band | Band pctile | Overall (n=989) | Overall pctile |
|---|---|---|---|---|---|
| Silvergate Bank | $10B–$100B | 2 / 128 | 99.2 | 8 | 99.3 |
| Silicon Valley Bank | >$100B | 1 / 35 | 100.0 | 26 | 97.5 |
| Signature Bank | >$100B | 2 / 35 | 97.1 | 60 | 94.0 |
| First Republic Bank | >$100B | 8 / 35 | 79.4 | 355 | 64.2 |
| Republic Bank (2024, out-of-window) | $1B–$10B | 86 / 826 | 89.7 | 95 | 90.5 |

With only three or four labeled events, these are presented as ranks and
distribution positions. Capture rates and lift statistics would be meaningless
at this sample size, so they are deliberately absent.

First Republic is the miss. The screen's rate-risk proxy is securities as a
share of assets, which is the Silicon Valley Bank profile. First Republic
parked its rate risk where these six metrics barely look: long fixed-rate
jumbo mortgages, funded by wealthy clients whose balances sat far above the
insurance cap. Its securities component scored below its band median at the
freeze. What fired for it was growth, uninsured share, and margin trend,
enough for 8th of 35 but nothing like the top-of-band signal the others gave.

## The false positives

The screen's false positives need the same accounting as its hits. Of
the hundred banks in the top decile of the frozen composite, taking the 90th
percentile within each band with ties included, 89 are still operating.
Three of the eleven that aren't are the labeled cases above, and the other
eight were acquired, not failed. The case-study page examines five of the
89 in detail, chosen after checking the FDIC's history endpoint for real
acquisition records: two genuine growth artifacts whose three-year growth came
from buying other banks (First Bank & Trust of Lubbock, which absorbed the
$1.85B AIMBank in late 2020, and SmartBank of Pigeon Forge, which absorbed
Sevier County Bank in 2021), and three banks whose unusual shape is simply
their business model, a wholesale-funded specialty lender, a brokerage bank
growing on affiliate sweep deposits, and a municipal-deposit bank whose
uninsured funding is collateralized in practice. The exhibits live in
`docs/backtest/` as CSVs and reproduce with the command above.

One naming trap for anyone reading the exhibits: the sample contains a
Signature Bank (FDIC cert 58264, a bank in the one-to-ten-billion band) that is
a different institution from the Signature Bank of New York (cert 57053) that
failed. Certificate numbers are the identity; names repeat.

## Limitations

The two that govern everything: I picked these six metrics knowing how 2023
ended, so this is a test of whether a simple peer screen can express a known
story in data available at the time, not a claim that I would have called it
in advance. And the FDIC's API serves current values, including amendments
filed after mid-2022, so the freeze reconstructs the mid-2022 view closely but
not as a true point-in-time vintage. Both statements appear wherever results
do, on the case-study page and in the README, not just here.

Two more limitations affect specific numbers. Winsorization saturates on
zero-inflated metrics: about 16% of brokered-share observations sit exactly at
the +5 cap because most smaller banks hold no brokered deposits at all, which
flattens distinctions among exactly the banks a reader most wants to compare
(the drill-down keeps an unclamped column for this reason). And the three-year
growth metric requires twelve quarters of in-scope history, so recent
threshold-crossers have no value for it and roughly half of the 2022-Q2
composites rest on five metrics rather than six. The companion count column
makes that visible wherever composites appear.
