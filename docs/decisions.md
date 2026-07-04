# Decisions

Architecture-level decisions and their full rationales, newest first.

- **2026-07-04** — Bank profiles stay one searchable page, not a URL per bank.
  I tried Evidence templated pages (`/bank-profile/[cert]`, one per institution)
  so the outlier and peer tables could deep-link to a bank's trends. The build
  works, but each page prerenders its own query results, so 1,325 banks emit
  ~15,000 files, and the GitHub Pages deploy fails to sync that many — it dies at
  `syncing_files` every time, while the single-page build (~106 MB across ~270
  files) deploys in a couple of minutes. So the Pages ceiling that actually bit
  me is file count, not the ~100 MB total size I'd been watching. The profile
  keeps a bank selector instead; genuine per-bank links would need a host built
  for the file count (Cloudflare Pages, Netlify). A second finding fell out of
  the same debugging: Pages allows exactly one Actions concurrency guard, on the
  deploy job. A second guard — even under a different group name, on the build
  job — fails every deploy at that same `syncing_files` step while Pages itself
  is healthy, so the build job runs unserialized and the lone `pages-deploy`
  guard stands. The rare build-vs-refresh warehouse race that a build guard would
  have covered is self-healing on the next clean run.

- **2026-07-04** — Business-model peer groups ship as a context layer, not a
  replacement. Three fixed, documented thresholds classify every bank-quarter
  (loans/assets < 0.20 is fee-and-custody, brokered share > 0.25 is
  wholesale-funded, securities/assets > 0.50 is securities-focused, everyone
  else lends for a living). Rules instead of clustering because every
  assignment must be explainable in one sentence, and fixed thresholds instead
  of fitted ones because there is nothing to fit without lying to myself. The
  outlier composite and the 2023 backtest stay on size bands exactly as
  published: changing the peer basis under a published result would silently
  rewrite it.

- **2026-07-03** — Hosting: Evidence static build on GitHub Pages. I originally
  planned on Evidence Cloud's free tier, but it was discontinued. The managed
  product is now Evidence Studio at $15/user/mo, and it drops support for
  local-DuckDB sources. Open-source Evidence is unchanged and officially
  documents GitHub Pages as a deploy target, so my Actions workflows rebuild
  the static site on every refresh, and MotherDuck stays the warehouse the
  build reads at CI time. Before committing to this I verified interactivity
  survives a static build: a dropdown driving a parameterized query re-filters
  a table on the statically-served production bundle, with queries running
  client-side via DuckDB-WASM (verified with a scratch page before the real
  pages replaced it). The build is ~87 MB, of which only ~428 KB is
  query-result data (the rest is app JS including DuckDB-WASM), comfortably
  within GitHub Pages limits.

- **2026-07-03** — Python pinned to 3.13, not 3.14. dbt-core doesn't support
  3.14 yet (its mashumaro/pydantic-v1 dependencies block it until dbt v2.0),
  and 3.13 is the newest version that dbt-core, dbt-duckdb, duckdb, and pandas
  all support today. uv downloads and pins the interpreter, so the repo doesn't
  depend on whatever Python the machine happens to have.

- **2026-07-03** — Third-party GitHub Actions pinned by commit SHA. My first CI
  run failed because `astral-sh/setup-uv` publishes no moving `v8` major tag.
  The fix is also the safer practice: pin the exact commit SHA with the version
  as a comment. A SHA can't be silently retargeted the way a tag can.
  GitHub-owned actions (checkout, setup-node, the Pages upload and deploy pair)
  ride their major tags; the SHA discipline is for third parties.
