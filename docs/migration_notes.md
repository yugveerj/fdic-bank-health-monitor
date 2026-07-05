# Migration notes — DuckDB → BigQuery dialect port (Phase B)

Every expression changed in the dbt project for the BigQuery port, per
PROJECT_SPEC_V2.md §4, plus the expressions deliberately left alone where the
equivalence is subtle. The parity gate (docs/migration_validation.md, once
run) is what proves these ports exact; this file is the record of what changed
and why each change is semantics-preserving.

## Changed expressions

### Staging

| file | was (DuckDB) | is (BigQuery) | note |
| --- | --- | --- | --- |
| stg_fdic__financials.sql | `strptime(REPDTE, '%Y%m%d')::date` | `parse_date('%Y%m%d', REPDTE)` | both error on malformed non-NULL input, NULL passes through |
| stg_fdic__financials.sql | `cast(X as double)` ×25 | `cast(X as float64)` | `DOUBLE` is not a BigQuery type name; plain CAST (not SAFE_CAST) keeps fail-fast on junk |
| stg_fdic__financials.sql | `where strptime(REPDTE,'%Y%m%d')::date <= '{{ var("as_of") }}'::date` | `where parse_date('%Y%m%d', REPDTE) <= date '{{ var("as_of") }}'` | the backtest freeze — defines the cohorts behind the frozen ranks; var contract (ISO date) unchanged |
| stg_fdic__institutions.sql | `try_cast(strptime(ESTYMD/ENDEFYMD, '%m/%d/%Y') as date)` | `parse_date('%m/%d/%Y', …)` | **strict, not SAFE.** — see "Date parsing strictness" below |
| stg_fdic__institutions.sql | `cast(ASSET/DEP as double)` | `cast(… as float64)` | |
| stg_fdic__failures.sql | `try_cast(CERT as integer)` | `safe_cast(CERT as integer)` | v1's try_cast was deliberate (1930s NULL certs); SAFE_CAST is its exact equivalent |
| stg_fdic__failures.sql | `try_cast(strptime(FAILDATE, '%m/%d/%Y') as date)` | `parse_date('%m/%d/%Y', FAILDATE)` | strict — see below; failure dates pin the 2023 backtest events |
| stg_fdic__failures.sql | `cast(QBFASSET/QBFDEP as double)` | `cast(… as float64)` | |
| stg_fred__h8.sql | `obs_date::date` | `cast(obs_date as date)` | `::` cast syntax is not GoogleSQL |
| stg_fred__h8.sql | `try_cast(value as double)` ×2 | `safe_cast(value as float64)` | deliberate leniency: FRED serves `.` for missing |
| sources.yml | `schema: main` | `schema: fdic_raw` | dbt-bigquery maps schema→dataset |
| sources.yml | `loaded_at_field: "strptime(REPDTE, '%Y%m%d')"` | `"parse_timestamp('%Y%m%d', REPDTE)"` | rendered verbatim into the freshness query; must return TIMESTAMP |
| sources.yml | `loaded_at_field: "obs_date::timestamp"` | `"cast(obs_date as timestamp)"` | |

### Intermediate

| file | was | is | note |
| --- | --- | --- | --- |
| int_bank_quarter_metrics.sql | `year(report_date) * 4 + quarter(report_date)` | `extract(year from report_date) * 4 + extract(quarter from report_date)` | bare `year()`/`quarter()` don't exist in BigQuery |
| int_bank_quarter_metrics.sql | `regr_slope(nim, quarter_index) over trailing_4q` | `safe_divide(covar_pop(nim, qi) over trailing_4q, var_pop(qi) over trailing_4q)` | see "regr_slope identity" below |
| int_peer_groups.sql | `100_000_000` / `10_000_000` / `1_000_000` | `100000000` / `10000000` / `1000000` | underscore digit separators are a DuckDB extension; GoogleSQL parse error. Same values — assets in thousands |

### Marts

| file | was | is | note |
| --- | --- | --- | --- |
| fct_bank_quarters.sql | `m.cert \|\| '_' \|\| strftime(m.report_date, '%Y%m%d')` | `cast(m.cert as string) \|\| '_' \|\| format_date('%Y%m%d', m.report_date)` | strftime doesn't exist and BigQuery `\|\|` won't coerce INT64; FORMAT_DATE keeps zero-padding, so keys are byte-identical |
| mart_peer_percentiles.sql, mart_model_percentiles.sql | `unpivot metrics on … into name metric value value` | `select * from metrics unpivot (value for metric in (…))` | DuckDB's standalone UNPIVOT statement → BigQuery's FROM-clause operator. Both exclude NULLs by default — that default is load-bearing (row counts feed every median/MAD and n_screen_metrics) |
| mart_peer_percentiles.sql ×2, mart_model_percentiles.sql ×2 | `median(x) over (partition by …)` | `percentile_cont(x, 0.5) over (partition by …)` | BigQuery has no MEDIAN. Exact PERCENTILE_CONT window, **never APPROX_QUANTILES** (hard rule). DuckDB MEDIAN is quantile_cont(0.5): both linearly interpolate at even n, so values are bit-comparable. BigQuery's window PERCENTILE_CONT allows PARTITION BY only — these usages comply |

### dbt tests + config

| file | was | is | note |
| --- | --- | --- | --- |
| tests/assert_assistance_not_marked_failed.sql | `count(*) filter (where resolution_type = 'FAILURE')` | `countif(resolution_type = 'FAILURE')` | GoogleSQL has no FILTER clause; countif is semantics-identical (NULL predicate rows counted by neither) |
| tests/assert_one_band_per_bank_quarter.sql | `1_000_000` | `1000000` | keep in sync with int_peer_groups thresholds |
| profiles.yml | duckdb local/md/backtest targets | bigquery dev/prod/backtest (oauth ADC, env-var project) | datasets: dbt_dev, analytics, dbt_backtest (BACKTEST_DATASET overridable) |
| dbt_project.yml | — | fct_bank_quarters partitioned by report_date, clustered by cert | pattern-practice at MB scale, honestly labeled (decisions.md) |

## Left alone on purpose (the equivalence depends on it)

- **Zero-MAD guards**: `case when peer_mad > 0 then (value - peer_median) /
  (1.4826 * peer_mad) …` is unchanged. DuckDB returns NULL on division by
  zero; BigQuery raises. The CASE guard means the division never executes with
  a zero denominator in either engine — do NOT "simplify" to SAFE_DIVIDE,
  which would silently mask a future regression the guard would surface.
- **`greatest(-5, least(5, …))` winsorization**: identical text, but BigQuery
  returns NULL if any argument is NULL where DuckDB skips NULLs. Inputs are
  provably non-null under the MAD guard, so no drift; keep the exact form —
  assert_robust_z_is_winsorized does float-exact `<>` comparison against it.
- **`cast(CERT as integer)`**: INTEGER is a valid INT64 alias in BigQuery.
- **`pow(assets_ratio, 1.0/3) - 1`** (3y CAGR): identical semantics for
  non-negative bases; a negative base would error in BigQuery vs NaN in
  DuckDB, but is unreachable (assets ≥ 0, zero denominator nullif-guarded).
- **Named window + `range between 3 preceding and current row`** over the
  INT64 quarter_index: valid BigQuery as written.
- **`int_business_models.sql`, `dim_banks.sql`, `mart_outlier_flags.sql`**:
  audited clean — no dialect-sensitive expressions.

## Date parsing strictness

v1's `try_cast(strptime(...) as date)` looks lenient but is not: strptime
itself raises on malformed non-NULL input (try_cast only guards the
TIMESTAMP→DATE step, which can't fail). So the v1 behavior is fail-fast, and
the port uses strict `parse_date`, not `SAFE.parse_date`. Verified against
the production-shaped warehouse before deciding: ESTYMD, ENDEFYMD (27,836
rows) and FAILDATE (4,115 rows) contain zero NULLs, zero empty strings, zero
unparseable values. If FDIC ever serves junk, the build fails loudly — same
as v1.

## regr_slope identity

BigQuery has no `regr_slope`. The replacement `covar_pop(y, x) / var_pop(x)`
over the same window is the textbook identity, with one caveat: regr_slope
restricts to rows where *both* arguments are non-null, while `var_pop(x)`
alone doesn't. That difference can only appear when some NIM values in the
4-quarter frame are NULL — exactly the rows where the `nim_obs_4q = 4` guard
already nulls `nim_trend_4q`. Everywhere the slope is exposed, the frame has
four non-null pairs and the two formulations are the same population.
`safe_divide` covers the single-observation frame (var_pop = 0), which
DuckDB's regr_slope also returns NULL for — and which the guard hides anyway.

## Known transitional breakage (on this branch, until ported)

- `scripts/run_backtest.py`, `scripts/check_new_quarter.py`,
  `scripts/export_dashboard_db.py` still target DuckDB and reference dbt
  targets that no longer exist on this branch. run_backtest is next
  (Phase B parity harness); the other two port with Phase C.
- `.github/workflows/ci.yml`'s fixture dbt build would fail on this branch's
  models; it only triggers on PRs, and the PR to main opens after cutover
  prep adapts it.
