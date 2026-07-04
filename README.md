# Bank Health Monitor

![CI](https://github.com/yugveerj/fdic-bank-health-monitor/actions/workflows/ci.yml/badge.svg)

A public dashboard that scores every US bank over $1B in assets against its
size peers each quarter, and a point-in-time backtest of the method against
the banks that failed in 2023. FDIC API → Python → DuckDB/MotherDuck → dbt →
Evidence, published on GitHub Pages and refreshed by CI with no manual steps.

**Live dashboard:** <https://yugveerj.github.io/fdic-bank-health-monitor/>

## Why this exists

Three of the four largest bank failures in US history happened within about
eight weeks in the spring of 2023, and the warning signs were sitting in
public quarterly filings: funding concentrated in uninsured deposits, balance
sheets heavy with rate-sensitive assets, growth that had outrun the peer
group. I wanted to know whether a straightforward peer-comparison screen,
built only on the FDIC's public data, would have surfaced those banks while
it still mattered.

## Results

Where the banks at the center of the 2023 stress ranked on my composite
screen, frozen at June 30, 2022 — nine months before the first of them
failed:

| Bank | Band | Rank in band | Band pctile | Overall rank (of 989) |
|---|---|---|---|---|
| Silvergate Bank (liquidated Mar 2023) | $10B–$100B | 2 / 128 | 99.2 | 8 |
| Silicon Valley Bank (failed Mar 2023) | >$100B | 1 / 35 | 100.0 | 26 |
| Signature Bank (failed Mar 2023) | >$100B | 2 / 35 | 97.1 | 60 |
| First Republic Bank (failed May 2023) | >$100B | 8 / 35 | 79.4 | 355 |
| Republic Bank (failed Apr 2024, out-of-window) | $1B–$10B | 86 / 826 | 89.7 | 95 |

Two caveats come with this table. The six metrics were chosen knowing how
2023 ended, so this demonstrates a screening method on historical data; it
is not an out-of-sample discovery. And the FDIC API serves current values,
including post-2022 amendments, so the freeze can only approximate the
mid-2022 view.

One command reproduces the table: `uv run python -m scripts.run_backtest`.
If you're deciding whether the code is worth reading, start there. The script
rebuilds the entire pipeline in a database whose raw financials are
physically truncated at the as-of date, then asserts that the frozen
composites match the production mart row for row, all 989 banks. Every
screen metric is built from trailing windows, so if any of them leaked future
data, the truncated rebuild could not match a mart computed over the full
panel. The script also pins the labeled banks to their published ranks, and a
fixture-scale version of the same proof runs on every pull request.

First Republic is the miss. My rate-risk proxy is securities as a share of
assets, which is the Silicon Valley Bank profile. First Republic parked its
rate risk where these six metrics barely look: long fixed-rate jumbo
mortgages, funded by clients whose balances sat far above the insurance cap.
Its securities component scored below its band median at the freeze; what
fired was growth, uninsured share, and margin trend, enough for 8th of 35.

The false positives are accounted for too. Of the hundred banks in the top decile of the
frozen composite (90th percentile within each band, ties included), 89 are
still operating; three of the eleven that aren't are the labeled banks above,
and the other eight were acquired. The case-study page examines five of the
89: two whose three-year growth came from buying other banks, and three whose
unusual shape is simply their business model. Full methodology:
[docs/backtest_method.md](docs/backtest_method.md).

## How the screen works

Six metrics, fixed before the backtest was built and never adjusted
afterward: uninsured-deposit share, brokered-deposit share, securities as a
share of assets, three-year asset growth, the four-quarter net interest
margin trend, and equity over assets. Each becomes a z-score against the
median and MAD of the bank's size band that quarter — median and MAD because
bank ratios have heavy tails, and a single extreme peer shouldn't be able to
mask or manufacture outliers.

The composite is the unweighted mean of whichever scores are available. With
three labels, fitting weights is how you lie to yourself, so I didn't. The
outlier screen shows the six metrics are close to uncorrelated, so the
unweighted average isn't double-counting a single signal.

## Limitations

The two caveats under the results table govern everything. Beyond those:

- Three failures and one voluntary liquidation is not a sample. It's a case
  study, and the page is titled accordingly.
- Quarterly data sees the setup, not the run. SVB went from stressed to gone
  in days; no quarterly screen catches that speed.
- The composite compares within size bands only, and the over-$100B band is
  broad: it puts SVB in the same peer group as JPMorgan. A business-model
  peer view exists on the explorer as context; the composite stays on size
  bands so the published backtest ranks never move.
- Uninsured-deposit figures are the banks' own reported estimates.

## What the tests caught

The best bugs in this project were in the data, not the code.

The FDIC's failures endpoint includes more than failures. It also carries
open-bank assistance records, which briefly marked Citibank and Bank of
America as failed banks in my first pass. The fix requires an actual FAILURE
resolution type, and a test now enforces it.

Winsorization saturates on zero-inflated ratios: most smaller banks report
zero brokered deposits, which collapses the MAD and pins 16% of
brokered-share z-scores exactly at the +5 cap. A bank with 20% brokered
funding and a bank with 99% were scoring identically. The composite keeps the
capped score for stability, and the drill-down keeps an unclamped column so
the resolution isn't lost.

There are more, including Depression-era failure records with null
certificate numbers and insured filers that aren't banks, plus the
verification work behind the ingested data: sixty asset values checked
against BankFind's own CSV exports, and all sixty matched. It's all in
[docs/data_quality.md](docs/data_quality.md).

## Architecture

![Architecture: FDIC and FRED APIs into cached Python ingestion, MotherDuck warehouse, dbt models, Evidence static build on GitHub Pages, all orchestrated by GitHub Actions](docs/architecture.png)

Ingestion is idempotent: a second full ingest leaves every table's row count
unchanged (27,836 institutions, 28,369 bank-quarters, 4,115 failure records
at last full check), because loads are keyed upserts. dbt runs 29 data tests
on every build, and the site is rebuilt from the warehouse on every deploy,
so nothing on the dashboard is typed in by hand.

## How to run

```bash
uv sync                                        # Python env (uv installs the pinned 3.13)
uv run python -m ingestion.run_all             # full ingestion (idempotent, safe to re-run)
cd dbt && DBT_PROFILES_DIR=. uv run dbt build  # models + tests (local DuckDB by default)
cd .. && uv run python -m scripts.export_dashboard_db   # marts -> dashboard source
cd dashboard && npm run sources && npm run dev # local dashboard preview
uv run python -m scripts.run_backtest          # reproduce the 2023 backtest + proof
```

In CI the same steps run against MotherDuck (`DBT_TARGET=md`); pushes rebuild
the site from the warehouse, and only the scheduled or manual refresh
re-ingests from the FDIC API. Pull requests run the full dbt build against a
committed sample of real API rows, so they never need secrets or network
access to the FDIC.

Copy `.env.example` to `.env` and fill in your keys. Nothing secret is
committed.

## Decisions

One line per decision; full rationales in [docs/decisions.md](docs/decisions.md).

- Hosting is open-source Evidence, static-built onto GitHub Pages
  (2026-07-03). Evidence Cloud's free tier was discontinued.
- Python is pinned to 3.13 (2026-07-03). dbt-core blocks 3.14 until dbt v2.0.
- Third-party GitHub Actions are pinned by commit SHA (2026-07-03). setup-uv
  publishes no moving major tag.
- Business-model peer groups ship as a context layer (2026-07-04). The
  composite and backtest stay on size bands so published results never move.
- Bank profiles stay a single searchable page (2026-07-04). Per-bank
  templated routes prerender ~15,000 files, more than the GitHub Pages deploy
  can sync; real deep-links would need a host built for that file count.
