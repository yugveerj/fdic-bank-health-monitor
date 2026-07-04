# Bank Health Monitor

![CI](https://github.com/yugveerj/fdic-bank-health-monitor/actions/workflows/ci.yml/badge.svg)

This is a public dashboard that scores every US bank over $1B in assets against
its size peers each quarter, then backtests the method against the banks that
failed in 2023. Stack: FDIC API → Python → DuckDB/MotherDuck → dbt → Evidence,
published on GitHub Pages and refreshed by CI with no manual steps.

**Live dashboard:** <https://yugveerj.github.io/fdic-bank-health-monitor/>

## Why this exists

Three of the four largest bank failures in US history happened within about eight
weeks in the spring of 2023, and the warning signs were sitting in public quarterly
filings: funding concentrated in uninsured deposits, balance sheets heavy with
rate-sensitive assets, growth that had outrun the peer group. I wanted to know
whether a straightforward peer-comparison screen, built only on the FDIC's public
data, would have surfaced those banks while it still mattered.

This repo is the answer. An automated pipeline scores every US bank above $1B in
assets against its size peers each quarter, and a point-in-time backtest freezes
the data at June 2022 and checks the 2023 failures against it. SVB ranks first in
its peer band at the freeze. First Republic doesn't, and the write-up doesn't hide
that.

## Architecture

![Architecture: FDIC and FRED APIs into cached Python ingestion, MotherDuck warehouse, dbt models, Evidence static build on GitHub Pages, all orchestrated by GitHub Actions](docs/architecture.png)

## Results

Where the banks at the center of the 2023 banking stress ranked on my composite
screen, frozen at 2022-06-30. That is nine months before the first failure.
Reproduce everything with `uv run python -m scripts.run_backtest` (it also
*proves* the freeze: a physically truncated rebuild must match the production
mart exactly).

| Bank | Band | Rank in band | Band pctile | Overall rank (of 989) |
|---|---|---|---|---|
| Silvergate Bank (liquidated Mar 2023) | $10B–$100B | 2 / 128 | 99.2 | 8 |
| Silicon Valley Bank (failed Mar 2023) | >$100B | 1 / 35 | 100.0 | 26 |
| Signature Bank (failed Mar 2023) | >$100B | 2 / 35 | 97.1 | 60 |
| First Republic Bank (failed May 2023) | >$100B | 8 / 35 | 79.4 | 355 |
| Republic Bank (failed Apr 2024, out-of-window) | $1B–$10B | 86 / 826 | 89.7 | 95 |

Two honesty notes govern this table: the metrics were chosen with knowledge of
the 2023 events (a methodology demonstration, not an out-of-sample discovery),
and the FDIC API serves current values that may include post-2022 amendments,
which makes the freeze approximate rather than exact. Full methodology:
[docs/backtest_method.md](docs/backtest_method.md).

## Limitations

- The six screen metrics were chosen with knowledge of the 2023 events. This
  demonstrates a methodology on historical data. It is not an out-of-sample
  discovery, and I don't present it as one.
- The FDIC API serves current values, including post-2022 amendments, so the
  freeze approximates the mid-2022 view rather than reproducing it exactly.
- Three failures and one voluntary liquidation is not a sample. It's a case study,
  and the page is titled accordingly.
- Quarterly data sees the setup, not the run. SVB went from stressed to gone in
  days; no quarterly screen catches that speed.
- Peer bands are size-only. The over-$100B band puts SVB next to JPMorgan, which
  flatters nobody's comparison. Business-model peer groups are the first upgrade
  I'd make.
- The composite is an unweighted average. With three labels, fitting weights is
  how you lie to yourself, so I didn't.
- Uninsured-deposit figures are the banks' own reported estimates.

## How to run

```bash
uv sync                                        # Python env (uv installs the pinned 3.13)
uv run python -m ingestion.run_all             # full ingestion (idempotent, safe to re-run)
cd dbt && DBT_PROFILES_DIR=. uv run dbt build  # models + tests (local DuckDB by default)
cd .. && uv run python -m scripts.export_dashboard_db   # marts -> dashboard source
cd dashboard && npm run sources && npm run dev # local dashboard preview
uv run python -m scripts.run_backtest          # reproduce the 2023 backtest + proof
```

In CI the same steps run against MotherDuck (`DBT_TARGET=md`); pushes rebuild the
site from the warehouse, and only the scheduled/manual refresh re-ingests from
the FDIC API.

Copy `.env.example` to `.env` and fill in your keys. Nothing secret is committed.

## What the tests caught

Two findings I'm keeping visible because they're the best argument for testing
data, not just code.

The FDIC's failures endpoint includes more than failures: it also carries
open-bank assistance records, which briefly marked Citibank and Bank of America
as failed banks in my first pass. The fix requires an actual FAILURE resolution
type, and a test now enforces it. Government data has semantics, and the
semantics are not always what the endpoint name says.

Winsorization saturates on zero-inflated ratios: most smaller banks report zero
brokered deposits, which collapses the MAD and pins 16% of brokered-share
z-scores exactly at the +5 cap. That quietly erases differences between the
banks you most want to compare. The composite keeps the clamped score for
stability, the drill-down keeps an unclamped column for resolution, and the
limitation is written down instead of discovered later.

[Full data-quality log](docs/data_quality_log.md).

## Decisions

One line per decision; full rationales in [docs/decisions.md](docs/decisions.md).

- **2026-07-03** — Hosting: open-source Evidence, static build on GitHub Pages
  (Evidence Cloud's free tier was discontinued).
- **2026-07-03** — Python pinned to 3.13 (dbt-core blocks 3.14 until dbt v2.0).
- **2026-07-03** — Third-party GitHub Actions pinned by commit SHA (setup-uv
  publishes no moving major tag).
