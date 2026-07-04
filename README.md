# FDIC Bank Health Monitor

![CI](https://github.com/yugveerj/fdic-bank-health-monitor/actions/workflows/ci.yml/badge.svg)

I'm building an automated analytics platform on FDIC public data that tracks the
financial health of US banks: API ingestion → DuckDB/MotherDuck → dbt-tested models →
an Evidence dashboard published to GitHub Pages, refreshed on a schedule by CI.

**Live dashboard:** <https://yugveerj.github.io/fdic-bank-health-monitor/>

## Problem statement

<!-- TODO(revise) -->
_Write-up coming once the first real data is flowing: what question this platform
answers, and for whom._

## Architecture

_Diagram coming with the automation work._

## Results

Where the banks at the center of the 2023 banking stress ranked on my composite
screen, frozen at 2022-06-30 — nine months before the first failure. Reproduce
everything with `uv run python -m scripts.run_backtest` (it also *proves* the
freeze: a physically truncated rebuild must match the production mart exactly).

| Bank | Band | Rank in band | Band pctile | Overall (n=989) |
|---|---|---|---|---|
| Silvergate Bank (liquidated Mar 2023) | $10B–$100B | 2 / 128 | 99.2 | 8 |
| Silicon Valley Bank (failed Mar 2023) | >$100B | 1 / 35 | 100.0 | 26 |
| Signature Bank (failed Mar 2023) | >$100B | 2 / 35 | 97.1 | 60 |
| First Republic Bank (failed May 2023) | >$100B | 8 / 35 | 79.4 | 355 |
| Republic Bank (failed Apr 2024, out-of-window) | $1B–$10B | 86 / 826 | 89.7 | 95 |

Two honesty notes govern this table: the metrics were chosen with knowledge of
the 2023 events (a methodology demonstration, not an out-of-sample discovery),
and the FDIC API serves current values that may include post-2022 amendments —
the freeze is approximate. Full methodology: [docs/backtest_method.md](docs/backtest_method.md).

## Limitations

<!-- TODO(revise) -->
_Honest limitations write-up comes with the backtest — including how metric selection
relates to hindsight, and what the FDIC API's current-values serving means for
point-in-time reconstruction._

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

Copy `.env.example` to `.env` and fill in your keys — nothing secret is committed.

## What the tests caught

_I log real data-quality catches here as they happen. Bank data will not be clean._

- **2026-07-03 — "Failed" banks that are alive and enormous.** While stress-testing
  the failure labels I found five currently active banks — Citibank and Bank of
  America among them — marked as failed. The FDIC endpoint is really "failures *and
  assistance*": it includes open-bank ASSISTANCE events (Citibank 2008, FirstBank
  Puerto Rico 1981) alongside true failures. My `is_failed` flag now requires
  `resolution_type = 'FAILURE'`. Without this, the 2023 backtest labels — and the
  rule that operating banks are never described as failed — would both have broken.

- **2026-07-03 — Insured filers that aren't banks.** A dbt relationship test failed
  on 123 bank-quarters whose certificate has no institutions record. They're real:
  Bank of China's US branch, Depository Trust Co, and four other insured non-bank
  filers report financials but aren't chartered US banks. The analytical universe is
  now defined as "institutions in the FDIC registry" — the raw layer keeps everything,
  the fact model applies the rule.

- **2026-07-03 — A z-score cap that erased the differences it was built to show.**
  I winsorize peer z-scores at ±5 so a single wild value can't dominate the
  composite — standard practice, but I checked what it does on my actual data:
  16% of brokered-deposit-share observations sit at exactly +5, because a third of
  $1–10B banks hold zero brokered deposits, which crushes the band's MAD and makes
  anything above ~18% share saturate. A 20%-brokered bank and a 99%-brokered bank
  were scoring identically. The composite keeps the cap (stability is the point);
  I added an unclamped z column so drill-downs keep their resolution, and the
  saturation is documented as a known limitation of the method.

- **2026-07-03 — NULL certificate numbers in Depression-era failure records.** My
  upsert guard rejects batches with duplicate keys, and the very first `/failures`
  load tripped it: 53 collisions on `(CERT, FAILDATE)`. The cause is 1930s failure
  records with no certificate number — six different banks all "failed" on
  1936-12-21 with `CERT` null. The fix: key failure records on the API's own `ID`
  field, which is unique on all 4,115 rows. The lesson I'm keeping: never assume a
  natural key holds across ninety years of records.

## Decisions

Why I made the architecture calls I made, newest first.

- **2026-07-03 — Hosting: Evidence static build on GitHub Pages.** I originally
  planned on Evidence Cloud's free tier, but it was discontinued — the managed
  product is now Evidence Studio at $15/user/mo, and it drops support for
  local-DuckDB sources. Open-source Evidence is unchanged and officially documents
  GitHub Pages as a deploy target, so my Actions workflows rebuild the static site
  on every refresh, and MotherDuck stays the warehouse the build reads at CI time.
  Before committing to this I verified interactivity survives a static build: a
  dropdown driving a parameterized query re-filters a table on the statically-served
  production bundle, with queries running client-side via DuckDB-WASM (see
  `dashboard/pages/static-build-check.md`). The build is ~87 MB — only ~428 KB of it
  is query-result data, the rest is app JS including DuckDB-WASM — comfortably within
  GitHub Pages limits.

- **2026-07-03 — Python pinned to 3.13, not 3.14.** dbt-core doesn't support 3.14
  yet (its mashumaro/pydantic-v1 dependencies block it until dbt v2.0), and 3.13 is
  the newest version that dbt-core, dbt-duckdb, duckdb, and pandas all support today.
  uv downloads and pins the interpreter, so the repo doesn't depend on whatever
  Python the machine happens to have.

- **2026-07-03 — Third-party GitHub Actions pinned by commit SHA.** My first CI run
  failed because `astral-sh/setup-uv` publishes no moving `v8` major tag. The fix is
  also the safer practice: pin the exact commit SHA (with the version as a comment) —
  a SHA can't be silently retargeted the way a tag can.
