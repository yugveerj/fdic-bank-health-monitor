# Decisions

Architecture-level decisions and their full rationales, newest first.

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
