# Looker Studio satellite — build guide (D4)

Looker Studio has no headless publish path, but its Linking API can hand you
a report with the data sources already wired — you click one URL, save, lay
out the charts once, and share. The saved report then doubles as a template:
any future re-point is one click.

## 1. One click: create the pre-wired report

Open this as the Google account that owns `fdic-monitor` (it becomes the
report and data-source owner; its credentials serve viewers):

```
https://lookerstudio.google.com/reporting/create?r.reportName=FDIC%20Bank%20Health%20Monitor%20-%20Looker%20Satellite&ds.*.connector=bigQuery&ds.*.type=TABLE&ds.*.projectId=fdic-monitor&ds.*.datasetId=analytics&ds.ds0.tableId=fct_bank_quarters&ds.ds0.datasourceName=fct_bank_quarters&ds.ds1.tableId=mart_outlier_flags&ds.ds1.datasourceName=mart_outlier_flags&ds.ds2.tableId=mart_h8_forecasts&ds.ds2.datasourceName=mart_h8_forecasts
```

Looker Studio opens an unsaved report named `FDIC Bank Health Monitor -
Looker Satellite` with three data sources attached. Click **Save** (or
"Edit and share") to persist it.

## 2. Build the pages (the one part no API can do)

Every design decision made in advance; ~20 minutes.

**Page 1 — "Sector overview"** (rename via Page → Manage pages):
1. Add a **Time series** chart: data source `fct_bank_quarters`, Dimension
   `report_date`, Metric `total_assets` (SUM) — set the metric's display
   name to "Total assets ($000s)".
2. Add a second Time series: Dimension `report_date`, Metric = **Record
   count**, name it "Banks in panel".
3. Add a **Scorecard** row: `Record count` filtered to the latest quarter is
   fiddly — instead use metrics `AVG roa_pct`, `AVG net_interest_margin_pct`
   from `fct_bank_quarters` with a date filter control (Add a control →
   Date range control bound to `report_date`).

**Page 2 — "Peer explorer"**:
1. Add a **Table** chart: data source `mart_outlier_flags`. Dimensions
   `cert`, `peer_band`; Metrics `composite_score` (AVG),
   `n_screen_metrics` (AVG). Sort: `composite_score` descending.
2. Add two controls: **Drop-down list** on `peer_band`, and a **Date range
   control** on `report_date`.
3. Chart → Style: enable heatmap coloring on the `composite_score` column.

**Page 3 — "Forecasts"**:
1. Add a **Time series**: data source `mart_h8_forecasts`, Dimension
   `forecast_week`, Metrics `forecast`, `lo_95`, `hi_95` (AVG each),
   Breakdown dimension `series_title` — or one chart per series if the
   breakdown is noisy.
2. Add a **Table**: Dimensions `series_id`, `method`; Metrics none needed
   beyond Record count — or bind it to `mart_h8_forecast_backtest` by
   adding that data source (Resource → Manage added data sources → Add) if
   you want the full MAPE/sMAPE table here.

**Every page**: add a **Text** box at the bottom, paste verbatim:

> Peer-relative statistics from public filings, never an assessment of any
> bank's condition. Source: FDIC BankFind Suite API.
> https://yugveerj.github.io/fdic-bank-health-monitor/

## 3. Configure credentials + caching (once)

Resource → Manage added data sources: each source should show **Owner's
credentials** (default — it's what lets anonymous viewers see data). Leave
data freshness at **12 hours**: it's the cache that keeps public viewers
from spending BigQuery quota. Free-tier math: the marts are megabytes and
the free tier is 1 TiB of query processing a month — this rounds to $0.

## 4. Publish

Share → Manage access → link settings → **Unlisted: anyone on the Internet
with the link can view**. Walk the "Review data access" dialog. Send back
the report URL (`lookerstudio.google.com/reporting/<id>`); the site nav and
README link to it from our side.

## Re-pointing later (template mode)

The saved report is a template. To clone it against a different dataset
(e.g. dev), read each source's **alias** from Resource → Manage added data
sources, then:

```
https://lookerstudio.google.com/reporting/create?c.reportId=<REPORT_ID>&ds.<alias>.connector=bigQuery&ds.<alias>.type=TABLE&ds.<alias>.projectId=fdic-monitor&ds.<alias>.datasetId=<dataset>&ds.<alias>.tableId=<table>
```
