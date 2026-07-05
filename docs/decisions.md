# Decisions

Architecture-level decisions and the reasoning behind them, newest first. The
README carries a one-line version of each; this file is the full account. Each
entry records what I chose, what I tried first, and what broke along the way.

## 2026-07-05 — Why we re-platformed: DuckDB/MotherDuck → BigQuery

Nothing was wrong with the v1 warehouse. MotherDuck ran this project's
megabytes without complaint, the free tier covered it, and DuckDB's SQL was
a pleasure. The move is about legibility, not capability: the same
engineering reads very differently to a recruiter or an ATS screen when it
runs on BigQuery, GCS, and Workload Identity Federation than when it runs on
a warehouse most screeners haven't heard of. v2 re-platforms onto named,
high-recognition tools without giving up anything that made v1 good — the
automation, the tests, the lineage, the frozen backtest.

The non-negotiable was that the numbers could not move. The migration ran
behind a hard parity gate, recorded in [migration_validation.md]
(migration_validation.md): raw row counts exact on every slice, all five
marts within 1e-9 of the MotherDuck originals (worst observed difference
6.4e-13), the 989-composite freeze equivalence proof reproduced, and the
published 2023 backtest ranks — Silvergate 2/128, SVB 1/35, Signature 2/35,
First Republic 8/35 — verified to the row on BigQuery before anything
merged. The dialect differences that could have silently shifted ranks
(BigQuery has no MEDIAN; approximate quantiles were never an option) are
itemized in [migration_notes.md](migration_notes.md), the biggest being
exact `PERCENTILE_CONT` windows for every median and MAD.

Auth ended up keyless everywhere: Workload Identity Federation worked on the
first configured run (one missing API enablement aside), so no
service-account JSON key exists — not in the repo, not in Actions secrets,
not on any laptop. Evidence turned out to need almost nothing: its page SQL
runs on DuckDB-WASM against extracted parquet regardless of the source, so
only the nine source queries moved to GoogleSQL and DuckDB stays in the
stack exactly where it earns its keep, in the browser.

## 2026-07-04 — v2 ingestion writes to BigQuery through staging + MERGE

First step of the v2 re-platform (PROJECT_SPEC_V2.md): on the `v2-bigquery`
branch, ingestion now lands in a BigQuery `fdic_raw` dataset instead of
DuckDB/MotherDuck. The write path is a new `ingestion/bq.py` beside the old
`ingestion/db.py` rather than a rewrite of it, because the DuckDB code stays
load-bearing until decommission: `main` keeps deploying from it, and the
migration parity checks read the old warehouse through it.

The contract is unchanged — upsert by key, safe to re-run — but the mechanism
had to change. DuckDB's delete-then-insert ran inside one transaction;
BigQuery has no transaction spanning a load job and DML, so the keyed write is
a load into a staging table followed by a single MERGE, which is atomic on its
own. The staging name is unique per call (and the table expires on its own if
a crash strands it): with a fixed name, two overlapping runs could truncate
each other's batch between load and MERGE and silently swap payloads — review
caught exactly that. CI serializes ingest runs anyway via a concurrency group,
belt and braces. Two guards got stricter in the port. Once a target table
exists, its schema drives every later staging load, so a quarter where a
column arrives all-null can't silently fork the column's type. And batches
with a NULL key are now rejected outright: key matching uses `=`, which never
matches NULL, so a null-keyed row would re-insert on every run — a hazard the
DuckDB version carried silently and none of our tables ever triggered.

Names, so nothing drifts later: dataset `fdic_raw`, env vars `GCP_PROJECT`
(required), `BQ_RAW_DATASET` and `BQ_LOCATION` (defaulted). Location is the
US multi-region so the eventual GA4 export and `bigquery-public-data` joins
don't cross regions. Local auth is plain ADC; CI is Workload Identity
Federation per the spec — the WIF-vs-key outcome gets its own entry once the
console setup lands.

The Phase A parity check (`scripts/raw_parity_check.py`) compares row counts
per quarter for financials, per series-week for FRED, and whole-table for the
snapshots. It demands exact equality on the overlap but tolerates BigQuery
being ahead of the old warehouse's high-water mark, clearly labeled: the
production refresh is scheduled and a branch ingest is not, so on most weeks
BigQuery legitimately holds a few days of FRED the Saturday run hasn't seen.
Anything missing or different inside the overlap still fails the run.

## 2026-07-04 — Bank profiles stay one searchable page, not a URL per bank

I tried Evidence's templated pages (`/bank-profile/[cert]`, one page per
institution) so the outlier and peer tables could deep-link straight to a
bank's trends. The build works. The deploy does not: each templated page
prerenders its own query results, so 1,325 banks emit roughly 15,000 files,
and the GitHub Pages deploy fails to sync that many. It dies at the
`syncing_files` step every time, while the single-page build, about 106 MB
across about 270 files, deploys in a couple of minutes. So the Pages limit
that matters in practice is file count, not the ~100 MB total size I had been
watching. The profile page keeps a bank selector instead. Genuine per-bank
links would need a host built for the file count, Cloudflare Pages or Netlify,
or Evidence dropping per-page query prerendering.

A second finding fell out of the same debugging: GitHub Pages tolerates
exactly one Actions concurrency guard, on the deploy job. A second guard, even
under a different group name on the build job, fails every deploy at that same
`syncing_files` step while Pages itself is perfectly healthy. So the build job
runs unserialized and the lone `pages-deploy` guard stands. The rare
build-versus-refresh warehouse race a build guard would have covered resolves
on the next clean run.

## 2026-07-04 — Business-model peer groups are context, not a new basis

Three fixed, documented thresholds classify every bank-quarter: loans under
20% of assets is fee-and-custody, brokered deposits over 25% of deposits is
wholesale-funded, securities over 50% of assets is securities-focused, and
everyone else lends for a living. Rules instead of clustering, because every
assignment has to be explainable in one sentence. Fixed thresholds instead of
fitted ones, because the project has too few labeled outcomes to fit or
validate cutoffs. And the whole thing ships as a context layer only: the outlier
composite and the 2023 backtest stay on size bands exactly as published,
because changing the peer basis underneath a published result would silently
rewrite it.

## 2026-07-03 — Hosting: Evidence static build on GitHub Pages

I originally planned on Evidence Cloud's free tier, but it was discontinued.
The managed product is now Evidence Studio at $15 per user per month, and it
drops support for local-DuckDB sources. Open-source Evidence is unchanged and
officially documents GitHub Pages as a deploy target, so my Actions workflows
rebuild the static site on every refresh, and MotherDuck stays the warehouse
the build reads at CI time.

Before committing to this I verified that interactivity survives a static
build: a dropdown driving a parameterized query re-filters a table on the
statically served production bundle, with queries running client-side via
DuckDB-WASM. I confirmed it with a scratch page before the real pages replaced
it. The build is about 87 MB, of which only about 428 KB is query-result data;
the rest is app JavaScript, most of it DuckDB-WASM itself. Comfortably within
GitHub Pages limits.

## 2026-07-03 — Python pinned to 3.13, not 3.14

dbt-core doesn't support 3.14 yet; its mashumaro and pydantic-v1 dependencies
block it until dbt v2.0. Python 3.13 is the newest version that dbt-core,
dbt-duckdb, duckdb, and pandas all support today. uv downloads and pins the
interpreter, so the repo doesn't depend on whatever Python the machine happens
to have installed.

## 2026-07-03 — Third-party GitHub Actions pinned by commit SHA

My first CI run failed because `astral-sh/setup-uv` publishes no moving `v8`
major tag. The fix turned out to be the safer practice anyway: pin the exact
commit SHA with the version as a comment. A SHA can't be silently retargeted
the way a tag can. GitHub-owned actions (checkout, setup-node, the Pages
upload and deploy pair) ride their major tags; the SHA discipline is for third
parties.
