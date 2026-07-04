# Decisions

Architecture-level decisions and the reasoning behind them, newest first. The
README carries a one-line version of each; this file is the full account. Each
entry records what I chose, what I tried first, and what broke along the way.

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
