# Migration validation — the Phase B parity gate

BigQuery rebuild verified against the current production (MotherDuck) marts
on 2026-07-05, per PROJECT_SPEC_V2.md §4. Everything below ran keyless in
branch CI (Workload Identity Federation); run IDs are the evidence trail.
Verdict up front: **the gate passes — no unexplained drift anywhere.**

## 1. Raw parity (Phase A gate) — PASS

Run 28725720279 (`v2 BigQuery ingest`): full ingest into `fdic_raw`, then
row counts against MotherDuck `md:fdic_bank_health`, sliced per quarter for
financials, per series-week for FRED, whole-table for the snapshots.

| table | slices compared | result |
| --- | --- | --- |
| raw_fdic_financials | every REPDTE quarter 2019-Q1 → present | exact match, all quarters |
| raw_fred_h8 | every (obs_date, series_id) pair | exact match, all pairs |
| raw_fdic_institutions | whole table | 27,836 = 27,836 |
| raw_fdic_failures | whole table | 4,115 = 4,115 |

The check tolerates BigQuery being ahead of the old warehouse's high-water
mark (the schedules never align); that tolerance was not needed — the two
warehouses matched exactly on every slice.

## 2. dbt build on BigQuery — 41/41 green

Run 28726071955 (`v2 BigQuery validation`): all 12 models and 29 tests build
green on the dev dataset (`dbt_dev`) from live `fdic_raw`.

## 3. Mart parity — PASS at 1e-9 absolute

Same run. Every mart compared cell-by-cell against production MotherDuck,
keyed on its grain; numerics within 1e-9 absolute, everything else exact,
key sets by anti-join in both directions.

| mart | rows (both sides) | max float diff |
| --- | --- | --- |
| dim_banks | 1,325 | 0.0 |
| fct_bank_quarters | 28,246 | 2.5e-15 |
| mart_outlier_flags | 28,246 | 1.2e-13 |
| mart_peer_percentiles | 366,012 | 6.4e-13 |
| mart_model_percentiles | 263,420 | 5.8e-14 |

Worst difference across ~687,000 compared rows: 6.4e-13 — four orders of
magnitude inside the gate. The z-scores, MADs, medians, and composites
reproduce to what is effectively floating-point identity.

## 4. The 2023 backtest reproduces exactly

Same run, `scripts/run_backtest.py` on BigQuery: frozen raw copies at
2022-06-30 (12,845 financials rows), full dbt build against the freeze,
equivalence proof, then the rank assertions.

- **Equivalence proven:** all 989 bank composites identical between the
  physically frozen build and the marts built from live raw, at 2022-06-30 —
  the screen uses only backward-looking data, on BigQuery as on DuckDB.
- **Frozen ranks verified — all five labeled banks match the published v1
  values:**

| bank | band | rank in band | pctile | overall |
| --- | --- | --- | --- | --- |
| Silvergate | $10B–$100B | 2/128 | 99.2 | 8/989 |
| Silicon Valley Bank | >$100B | 1/35 | 100.0 | 26/989 |
| Signature | >$100B | 2/35 | 97.1 | 60/989 |
| First Republic | >$100B | 8/35 | 79.4 | 355/989 |
| Republic (out-of-window, 2024) | $1B–$10B | 86/826 | 89.7 | 95/989 |

- **Exhibits:** the regenerated docs/backtest CSVs differ from the committed
  v1 files only in float text rendering (DuckDB's COPY vs pandas to_csv);
  parsed and compared numerically they are identical — max difference
  1.6e-14 on ranked_full.csv, with every rank, band, name, and count equal.
  The committed exhibits stay as they are; there is nothing to update.

## 5. Drift found and explained (none of it numeric)

Two failures happened on the way to green, both fixed and recorded:

1. **`mart_model_percentiles` build error** (run 28725933225): `select f.*,
   m.business_model` projected a duplicate column DuckDB had silently
   tolerated; BigQuery rejects it as ambiguous. Fixed with
   `select f.* except (business_model)` — row semantics untouched
   (migration_notes.md). A build error, not drift.
2. **Comparison-harness artifacts** (same run): the parity script flagged
   Timestamp-vs-date type mismatches and NULL-on-both-sides cells as
   differences (pandas makes `None != None` true). Fixed in the harness —
   dates normalize to ISO strings, mutual NULLs count as agreement — with
   each artifact pinned in tests/test_mart_parity.py. The 1e-9 tolerance was
   not changed. Measurement error, not drift.

No unexplained numeric drift remains. Per CLAUDE.md this gate blocks
cutover; it is now open. Cutover itself (merge to `main`, Evidence on
BigQuery, MotherDuck decommission) is Phase C and needs owner approval.

## 6. Postscript: cutover and decommission (2026-07-05, owner-approved)

Production merged and deployed from BigQuery the same day; all six dashboard
pages verified on the built artifact before merge, CI (including the fixture
backtest on ephemeral datasets), the weekly refresh, and the quarterly
detector all green end-to-end on the new stack. The final MotherDuck
snapshot — all 9 tables, 749,133 rows total, with a row-count manifest —
landed in `gs://fdic-monitor-archive/motherduck_final_20260705/` (run
28727995118) before the database was dropped (run 28728015870) and the
MOTHERDUCK_TOKEN secret deleted. The parity-check harnesses and the DuckDB
write path were removed with the decommission; they live in git history at
the runs cited above.
