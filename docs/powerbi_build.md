# Power BI + Power Query satellite — build guide (backlog, spec §6b)

A click-by-click script for the owner's Windows PC. Every design decision is
already made — if a step is ambiguous, that's a bug in this document. Two
artifacts come out of one session:

1. A PBIX on the **same Google Sheet extract the Tableau workbook reads**
   (`peer_percentiles` + `bank_trends`, written by `reporting/tableau_sheet.py`
   on every deploy). The Get Data / transform step *is* Power Query; section 3
   is the documented applied-steps artifact. Three DAX measures back the DAX
   claim. Published to the web on a free account, manual monthly refresh.
2. A Power Query-connected Excel workbook refreshing from the published GCS
   report (`reports/latest.xlsx`), committed to the repo.

One honest substitution up front: the spec's example measures say "deposit
growth", but the trimmed Sheet extract carries deposit *shares* and
`total_assets_bn` — no deposit level (the Sheet has a cell budget and no
business being a warehouse). The growth measures therefore run on total
assets. Same shape, same DAX, honest column.

Footer text used on the report page and in the Excel workbook, verbatim
(same as the site, Tableau, and Looker):

> Peer-relative statistics from public filings, never an assessment of any
> bank's condition. Source: FDIC BankFind Suite API.
> https://yugveerj.github.io/fdic-bank-health-monitor/

## 1. Prereqs

- Windows PC (confirmed available).
- **Power BI Desktop**, free, from the Microsoft Store (or
  aka.ms/pbidesktopstore). No license needed to build.
- A **Power BI service account** for publishing. The service rejects consumer
  addresses (gmail etc.) — you need a work-or-school Microsoft account; the
  free Fabric license that comes with it is enough for My workspace +
  Publish to web. No Pro required.
- **Excel** with Power Query (2016 or later; Microsoft 365 fine) for the
  second artifact.

## 2. One-time: make the Sheet link-viewable

The PBIX reads the Sheet through its CSV export endpoint, which answers
anonymously only if the Sheet is link-viewable. It currently isn't (it's
shared to the service account and you).

1. Open the Sheet (ID `1SEiXqOMMtoUWezdZFc2l3cpsrDFmkWrvfN_x0k_AtaU`) →
   **Share** → General access → **Anyone with the link**, role **Viewer**.
2. Verify: paste this into a browser —

   ```
   https://docs.google.com/spreadsheets/d/1SEiXqOMMtoUWezdZFc2l3cpsrDFmkWrvfN_x0k_AtaU/gviz/tq?tqx=out:csv&sheet=peer_percentiles
   ```

   A CSV should download. If you get a Google sign-in page instead, the
   sharing didn't take.

This exposes nothing new: the Sheet holds only the trimmed peer-relative
extract from public filings, the same rows already public in the Tableau
workbook and on the site.

Why the Web connector and not the native Google Sheets connector: the native
connector wants an OAuth sign-in and stores a per-machine Google credential;
the CSV endpoint needs no credential at all, returns deterministic CSV, and
refreshes identically in Desktop and the service. Dumber is better here.

## 3. Get Data + Power Query (the applied-steps artifact)

Three queries: one per worksheet, plus a small Banks dimension derived in
Power Query. Expect roughly 14,500 rows in peer_percentiles and 12,500 in
bank_trends — loads are instant.

### 3a. peer_percentiles

1. Power BI Desktop → **Get Data → Web** → paste:

   ```
   https://docs.google.com/spreadsheets/d/1SEiXqOMMtoUWezdZFc2l3cpsrDFmkWrvfN_x0k_AtaU/gviz/tq?tqx=out:csv&sheet=peer_percentiles
   ```

2. If a credentials dialog appears: **Anonymous**, apply to
   `https://docs.google.com/`. The CSV preview opens (if you get an HTML
   navigator instead, revisit section 2).
3. Click **Transform Data**. Rename the query `peer_percentiles`
   (Query Settings → Name).
4. The Applied Steps list you should end with — exactly these three:
   1. **Source** — `Csv.Document(Web.Contents("…"))`, comma-delimited,
      encoding 65001.
   2. **Promoted Headers** — first CSV row becomes the header
      (`cert, bank_name, peer_band, metric, value, robust_z, peer_median`).
   3. **Changed Type** — set each column, correcting any wrong guesses:
      - `cert` — Whole Number
      - `bank_name` — Text
      - `peer_band` — Text
      - `metric` — Text
      - `value` — Decimal Number
      - `robust_z` — Decimal Number
      - `peer_median` — Decimal Number

   No null-filter step is needed — the export writes a clean rectangle. If
   the preview ever shows trailing blank rows, add one **Filtered Rows**
   step (`bank_name` is not null) after Changed Type and note it here.

### 3b. bank_trends

1. In the Power Query editor: **New Source → Web** → paste the same URL with
   `&sheet=bank_trends`. Rename the query `bank_trends`.
2. Applied Steps, exactly:
   1. **Source** — as above.
   2. **Promoted Headers**.
   3. **Changed Type**:
      - `cert` — Whole Number
      - `bank_name` — Text
      - `report_date` — Date
      - `peer_band` — Text
      - `business_model` — Text
      - `total_assets_bn` — Decimal Number
      - `roa_pct` — Decimal Number
      - `net_interest_margin_pct` — Decimal Number
      - `equity_to_assets` — Decimal Number
      - `uninsured_deposit_share` — Decimal Number
      - `brokered_deposit_share` — Decimal Number
      - `securities_to_assets` — Decimal Number
      - `loans_to_deposits` — Decimal Number
      - `efficiency_ratio_pct` — Decimal Number
      - `noncurrent_loans_ratio_pct` — Decimal Number

   `report_date` arrives as ISO `YYYY-MM-DD` and must land as Date. If it
   comes through as Text your locale is mis-parsing it: right-click the
   column → Change Type → **Using Locale** → Date, English (United States).

### 3c. Banks (dimension)

Both fact tables key on `cert` many times over (one row per metric, one row
per quarter), so a shared dimension carries the bank slicer:

1. Right-click `bank_trends` in the query list → **Reference**. Rename the
   new query `Banks`.
2. Applied Steps, exactly:
   1. **Source** — `bank_trends`.
   2. **Removed Other Columns** — keep `cert`, `bank_name` (select both →
      right-click → Remove Other Columns).
   3. **Removed Duplicates** — select the `cert` column only → right-click
      → Remove Duplicates.
3. **Close & Apply.**

## 4. Data model

Model view (third icon, left rail):

1. Delete any relationship Power BI auto-created directly between
   `peer_percentiles` and `bank_trends` — cert-to-cert there is
   many-to-many and useless.
2. Create (drag `cert` onto `cert`), if autodetect didn't already:
   - `Banks[cert]` → `bank_trends[cert]` — one-to-many, single direction.
   - `Banks[cert]` → `peer_percentiles[cert]` — one-to-many, single
     direction.
3. Data pane: select each `cert` column → Column tools → Summarization →
   **Don't summarize** (it's an ID, not a measure).

That's the whole model: one dimension, two facts, star-shaped. One bank
slicer on `Banks[bank_name]` now drives both tables.

## 5. DAX measures (paste as written)

No date table is marked, and `report_date` is quarter-end snapshots — so no
`DATEADD`/`PREVIOUSQUARTER`; the self-contained pattern below needs nothing
but the column. Create each with **Modeling → New measure** while the named
table is selected in the Data pane.

**On `bank_trends` — `QoQ Asset Growth %`.** The latest quarter's total
assets versus the immediately preceding quarter, in the current filter
context — read it with a single bank selected; with no bank selected it is
the panel-wide aggregate.

```dax
QoQ Asset Growth % =
VAR LatestDate = MAX ( bank_trends[report_date] )
VAR PriorDate =
    CALCULATE ( MAX ( bank_trends[report_date] ), bank_trends[report_date] < LatestDate )
VAR Latest =
    CALCULATE ( SUM ( bank_trends[total_assets_bn] ), bank_trends[report_date] = LatestDate )
VAR Prior =
    CALCULATE ( SUM ( bank_trends[total_assets_bn] ), bank_trends[report_date] = PriorDate )
RETURN
    DIVIDE ( Latest - Prior, Prior )
```

**On `bank_trends` — `YoY Asset Growth %`.** Same numerator, but against the
quarter exactly four quarters back; blank when the bank wasn't in the panel
a year ago (`DIVIDE` handles it).

```dax
YoY Asset Growth % =
VAR LatestDate = MAX ( bank_trends[report_date] )
VAR YearAgo = EDATE ( LatestDate, -12 )
VAR Latest =
    CALCULATE ( SUM ( bank_trends[total_assets_bn] ), bank_trends[report_date] = LatestDate )
VAR Prior =
    CALCULATE ( SUM ( bank_trends[total_assets_bn] ), bank_trends[report_date] = YearAgo )
RETURN
    DIVIDE ( Latest - Prior, Prior )
```

**On `peer_percentiles` — `Delta to Peer Median`.** With one bank and one
metric in context (the two slicers, or a table row), this is the bank's raw
value minus its size band's median for that metric, in the metric's own
units.

```dax
Delta to Peer Median =
AVERAGE ( peer_percentiles[value] ) - AVERAGE ( peer_percentiles[peer_median] )
```

Formatting (Measure tools, with the measure selected): the two growth
measures **Percentage, 1 decimal**; the delta stays a plain decimal — its
units vary by metric (shares are 0–1 fractions, some metrics are percents),
so a fixed % format would lie.

## 6. Report page (one page, modest on purpose)

Name the page `Peer explorer`.

1. **Slicer** (top left): `Banks[bank_name]`. Format → Slicer settings →
   Selection → **Single select**. Pick any large bank as the saved default.
2. **Slicer** (below it): `peer_percentiles[metric]`, Single select, default
   `uninsured_deposit_share` (same default as the Tableau workbook). The
   delta card needs exactly one metric in context to mean anything.
3. **Line chart** (top right): X-axis `bank_trends[report_date]`, Y-axis
   `total_assets_bn` set to **Average** (one row per bank-quarter, so
   average = the value). Title: `Total assets ($B), last 12 quarters`.
4. **Three cards** in a row: `QoQ Asset Growth %`, `YoY Asset Growth %`,
   `Delta to Peer Median`.
5. **Table** (bottom): from `peer_percentiles` — `metric`, then `value`,
   `robust_z`, `peer_median` each set to Average. Sort by `robust_z`
   descending. This is the bank-versus-band readout for the selected bank.
6. **Text box**, full width at the very bottom: paste the footer text from
   the top of this document, verbatim. 9 pt, grey.

Save the file as `fdic_peer_satellite.pbix` (it gets committed under
`powerbi/` from our side — see section 9).

## 7. Publish to web (free) + monthly refresh

Publish to web is deliberately, irrevocably public — that is the point, and
the data is peer-relative statistics from public filings.

1. Desktop: **File → Publish → Publish to Power BI** → sign in → **My
   workspace** → Select.
2. Click the "Open in Power BI" link when the publish dialog finishes.
3. In the service, with the report open: **File → Embed report → Publish to
   web (public)** → **Create embed code** → **Publish**. Copy the
   `app.powerbi.com/view?r=…` link (that's the hand-back URL; the iframe
   snippet is offered too but the link is what the site needs).
4. If "Publish to web" is missing or greyed out: gear icon → **Admin
   portal → Tenant settings → Export and sharing settings → Publish to
   web** → Enabled. On a single-user tenant you are the admin; on a real
   org tenant the admin has to flip it, and if they won't, stop and say so —
   don't work around it.

**Refresh, documented and manual:** no gateway, no service credentials, no
schedule. Once a month (calendar reminder; the peer data only changes
quarterly anyway):

1. Open the PBIX in Desktop → **Home → Refresh** (re-pulls both CSVs,
   anonymously).
2. **File → Publish → Publish to Power BI** → same workspace → **Replace**
   when prompted.
3. The existing embed code picks up the new data on its own — same URL,
   nothing to re-embed; allow up to an hour for the public cache.

## 8. Excel Power Query workbook (same session)

One workbook that refreshes from the published GCS report. Source of truth:

```
https://storage.googleapis.com/fdic-monitor-reports/reports/latest.xlsx
```

Query the **MoversData** table (on the PivotData sheet), not a band sheet:
MoversData is a defined Excel Table, so the Navigator addresses it by name,
it carries its own headers, and its reference resizes with the row count
each quarter. The band sheets are two stacked Risers/Fallers blocks with
title rows at floating positions — parsing those would be row-index
archaeology.

1. New blank workbook → **Data → Get Data → From Web** → paste the URL
   above. Credentials, if asked: **Anonymous**, level
   `https://storage.googleapis.com/` (the bucket is public).
2. In the Navigator, pick **MoversData** (table icon — not the PivotData
   sheet entry) → **Transform Data**.
3. Applied Steps, exactly:
   1. **Source** — `Excel.Workbook(Web.Contents("…"))`.
   2. **Navigation** — the MoversData table (headers come with it; no
      Promote Headers step).
   3. **Removed Columns** — remove `delta`. It arrives entirely null:
      the generator writes it as a live Excel formula with no cached
      value, and Power Query reads cached values, not formulas.
   4. **Added Custom** — name `delta`, formula
      `= [composite] - [composite_prior]`.
   5. **Changed Type** — `peer_band` Text, `bank_name` Text, `cert` Whole
      Number, `composite` Decimal, `composite_prior` Decimal, `delta`
      Decimal, and all six z columns (`z_uninsured_share`,
      `z_brokered_share`, `z_securities_share`, `z_asset_growth_3y`,
      `z_nim_trend`, `z_equity_ratio`) Decimal.
4. **Close & Load To… → Table**, new worksheet; rename the worksheet
   `movers`.
5. Rename the leftover blank sheet `About` and paste the footer text from
   the top of this document into A1.
6. Save as `reporting/peer_report_powerquery.xlsx` in your repo checkout.
   It's committed as-is: anyone who opens it can **Data → Refresh All** and
   pull the current quarter from the public bucket on demand. That refresh
   path — not the frozen numbers inside — is the artifact.

## 9. Hand back

Send back, so the repo side can be finished:

1. The publish-to-web URL (`app.powerbi.com/view?r=…`).
2. The `fdic_peer_satellite.pbix` file — it gets committed under `powerbi/`
   next to this doc's applied-steps record.
3. The saved `reporting/peer_report_powerquery.xlsx` (or push the commit
   yourself if you're set up).
4. One line confirming which quarter the cards showed after refresh — a
   cheap sanity check that the Sheet, the PBIX, and the GCS report all
   agree.

The site nav and README link to the published report from our side, same as
the Tableau and Looker satellites.
