# AGENTS.md — FDIC Bank Health Monitor

## What this project is
Portfolio project #1: an automated analytics platform on FDIC public data
(ingestion → DuckDB/MotherDuck → dbt → Evidence static build on GitHub Pages),
ship target **Sept 1, 2026**. Full build spec: `PROJECT_SPEC.md`.
**This file supersedes PROJECT_SPEC.md wherever they conflict.**

## Mode: autonomous completion
Optimize for completing Phases 1–5 correctly and with maximum momentum.
- Do NOT quiz, teach, pause for comprehension checks, or ask gate questions.
- At any decision fork: pick the option most consistent with PROJECT_SPEC.md,
  record it in `docs/BUILD_LOG.md`, and continue.
- Post a short plan at each phase start and a short summary at each phase end
  (links, what changed, anything to verify) — then keep going.
- Stop and ask ONLY when: (a) blocked on credentials/accounts or repo settings,
  (b) anything would cost >$10/month or >$25 one-time, (c) an action is
  irreversible outside this repo, (d) a spec fallback trigger fires, or
  (e) data integrity is at risk and the spec doesn't resolve it.

## Voice and attribution (all tracked content — no exceptions)
- The public repo speaks in the owner's first-person voice. Every tracked file —
  README, public docs, code comments, dashboard prose, commit messages — is
  written as the owner: "I chose robust z-scores because…", "My screen flags…".
- Never write "Codex", "AI", "the assistant", "the model", "the user", or any
  reference to this workflow in tracked files or commit messages.
- Commit messages: plain first-person engineering style ("Add FDIC financials
  ingestion with pagination and raw caching"). No meta-narration, no attribution
  trailers, no generated-with lines.
- `.Codex/settings.json` must contain `{"attribution": {"commit": "", "pr": ""}}`
  (verify the current key against Codex's own settings docs; add the
  legacy `"includeCoAuthoredBy": false` alongside it — harmless if deprecated).
- **Internal working files are never committed:** `AGENTS.md`, `PROJECT_SPEC.md`,
  `docs/BUILD_LOG.md`, `docs/REVIEW_GUIDE.md`, and `.Codex/` are gitignored and
  live only on this machine. Public docs that ARE committed: README,
  `docs/verification.md`, `docs/backtest_method.md`, architecture diagram.
- Draft marker in public files is neutral: `<!-- TODO(revise) -->`. The master
  "make these yours" checklist lives in REVIEW_GUIDE.md (untracked).

## The review ledger (mandatory — untracked, local only)
- **`docs/BUILD_LOG.md`** — chronological, terse, first person: every significant
  decision (what / why / alternative rejected), every bug and fix, every
  data-quality finding.
- **`docs/REVIEW_GUIDE.md`** — every gate question from PROJECT_SPEC.md §7 plus
  new ones real decisions raise; each with a concise model answer written in
  first person (so the owner can rehearse it verbatim) and file pointers.
  Includes the "Make these yours" list of TODO(revise)-marked passages.

## Hard rules (unchanged — correctness, not pedagogy)
- IMPORTANT: Never fabricate, simulate, or hand-type data values. If an API
  blocks you, stop and report — do not fill gaps.
- IMPORTANT: Never use FDIC field codes, FRED series IDs, or endpoint paths from
  memory. Verify each against the saved field dictionary in `docs/` AND one live
  API response before use.
- Never weaken, skip, or mock a test to make CI green.
- Statistical-neutral language only about currently operating banks, everywhere.
  Failure language appears only on the 2023 backtest page.
- Secrets live in `.env` (gitignored) locally and GitHub Actions secrets in CI
  (`MOTHERDUCK_TOKEN`, `FRED_API_KEY`). Never in code, logs, or commits.
- Default to free tiers; the cost stop-trigger above governs anything paid.
- No scope beyond PROJECT_SPEC.md — log temptations in BUILD_LOG.md instead.
- Polite API usage: rate limits, raw caching, idempotent ingestion.

## Git
Small single-purpose commits, first-person messages, push to `main` freely;
never force-push (one documented exception was granted 2026-07-03 for the
history reset — it does not recur). No per-commit approval; the human reviews
at phase summaries.

## Stack (as built)
- Python 3.13 (uv-pinned; dbt-core blocks 3.14), managed with `uv`
- Warehouse: DuckDB local dev; MotherDuck free tier as shared/CI target
- Transform: dbt-core + dbt-duckdb
- Dashboard: open-source Evidence, static build on GitHub Pages via Actions
- CI/CD: GitHub Actions; third-party actions pinned by commit SHA
- Public repo, MIT license

## Commands
- `uv run python -m ingestion.run_all` — full ingestion (idempotent)
- `cd dbt && uv run dbt build` / `uv run dbt docs generate`
- `cd dashboard && npm run sources && npm run dev` — local preview
- `cd dashboard && npm run build` — static build (what Pages deploys)
