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

_The centerpiece will be a backtest: whether a peer-group outlier screen, frozen to
data available in mid-2022, would have flagged the 2023 bank failures. Results table
lands here when it's reproducible end to end._

## Limitations

<!-- TODO(revise) -->
_Honest limitations write-up comes with the backtest — including how metric selection
relates to hindsight, and what the FDIC API's current-values serving means for
point-in-time reconstruction._

## How to run

```bash
uv sync                              # Python env (uv installs the pinned 3.13)
uv run python -m ingestion.run_all   # full ingestion (idempotent, safe to re-run)
cd dbt && uv run dbt build           # models + tests
cd dashboard && npm run sources && npm run dev   # local dashboard preview
```

Copy `.env.example` to `.env` and fill in your keys — nothing secret is committed.

## What the tests caught

_I log real data-quality catches here as they happen. Bank data will not be clean._

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
