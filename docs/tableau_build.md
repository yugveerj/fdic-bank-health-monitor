# Tableau Public satellite — build paths

Published 2026-07-05:
<https://public.tableau.com/app/profile/yugveer.jain/viz/FDICBankHealthMonitorPeerSatellite/Peerexplorer>

## Path A (the one that shipped): the CI-packaged workbook

Tableau Desktop Public Edition refuses to open live-connection workbooks
(extracts are required at load, verified on 2026.1 and 2026.2), so the
deliverable is a packaged .twbx with real Hyper extracts baked in:

1. Actions → **Tableau twbx build** → Run workflow. It queries the marts,
   writes the extracts with the Hyper API, and uploads the artifact
   (`tableau/build_twbx.py`; workbook XML from `tableau/build_twb.py`,
   authored against real Desktop-2026 workbooks and adversarially reviewed).
2. Download the artifact, unzip it, double-click `fdic_peer_satellite.twbx`
   — it opens straight to the dashboards, no sign-in needed.
3. **File → Save to Tableau Public As…** → `FDIC Bank Health Monitor — Peer
   Satellite`.
4. Optional daily sync: save the Google credential in your Tableau Public
   web settings, then toggle **Keep this data in sync** on the workbook
   page. Without it, the documented fallback is a quarterly republish —
   rerun the workflow, download, open, Save (the peer data only changes
   quarterly anyway).

Republish the same way whenever the dashboards themselves change.

## Path B (fallback): exact build script

A click-by-click script executed mechanically in Tableau Desktop. Every
design decision is already made — if a step is ambiguous, that's a bug in
this document.

The data is already flowing: the deploy pipeline writes two worksheets to
the shared Google Sheet on every run (`peer_percentiles` — current quarter,
all banks × 14 metrics; `bank_trends` — twelve quarters of trimmed
fundamentals). Tableau connects to that Sheet and refreshes daily.

Footer text used on BOTH dashboards, verbatim (same as the site):

> Peer-relative statistics from public filings, never an assessment of any
> bank's condition. Source: FDIC BankFind Suite API.
> https://yugveerj.github.io/fdic-bank-health-monitor/

## 0. Connect the data (once)

1. Open Tableau Desktop Public Edition → **Connect → To a Server → Google Drive**
   (older versions: **Google Sheets**). Sign in with the account that owns the
   Sheet; allow access.
2. Pick the sheet named after this project (ID `1SEiXqOMMtoUWezdZFc2l3cpsrDFmkWrvfN_x0k_AtaU`).
3. The two tabs appear in the left rail. Drag **peer_percentiles** onto the
   canvas. Verify columns: cert, bank_name, peer_band, metric, value,
   robust_z, peer_median.
4. **Data → New Data Source** → same Google Sheet → drag **bank_trends**
   onto the canvas. Verify it shows report_date as Date. If it's a string:
   right-click report_date → Change Data Type → Date.
5. In each data source: right-click **cert** → Convert to Dimension (it's an
   ID, not a measure).

## 1. Worksheet "Distribution" (data source: peer_percentiles)

1. New worksheet, name it `Distribution`.
2. Drag **value** to **Columns**. Right-click the pill → **Dimension**.
3. Drag **bank_name** to **Detail** on the Marks card.
4. Marks type dropdown: **Circle**.
5. Drag **robust_z** to **Color**. Click Color → Edit Colors →
   palette **Red-Blue Diverging**, tick **Reversed**, click Advanced →
   fix Start `-5`, Center `0`, End `5` → OK.
6. Drag **peer_band** to **Filters** → select `$1B-$10B` only → OK.
   Right-click the filter pill → **Show Filter**. On the shown filter card's
   menu (top-right caret) → **Single Value (list)**.
7. Drag **metric** to **Filters** → select `uninsured_deposit_share` → OK →
   Show Filter → Single Value (list).
8. Drag **value** to Rows? — **No.** Leave Rows empty (a one-axis strip).
9. Tooltip (Marks card → Tooltip): keep defaults, add `peer_median` by
   dragging **peer_median** to Tooltip.
10. Title (double-click worksheet title): `Where every bank sits in its band`.

## 2. Worksheet "Tails" (data source: peer_percentiles)

1. New worksheet, name it `Tails`.
2. Drag **bank_name** to **Rows**, **value**, **robust_z**, **peer_median**
   each to the **Text/Measure Values** area (drag onto the canvas center —
   Tableau builds a text table; ensure Measure Values holds all three,
   aggregation on each pill set via right-click → **Attribute**).
3. Right-click **bank_name** on Rows → Sort → By field: robust_z,
   Descending, aggregation Maximum.
4. Drag **robust_z** to **Filters** → At Least `2` → OK. (The table shows
   the +2σ tail; the dashboard title explains.)
5. Apply the same two filters as Distribution: right-click the peer_band
   filter on that sheet → **Apply to Worksheets → Selected Worksheets** →
   tick `Tails`. Repeat for the metric filter.
6. Title: `Beyond +2 robust standard deviations`.

## 3. Dashboard "Peer explorer"

1. New dashboard, name `Peer explorer`. Size: Automatic.
2. Drag `Distribution` in; drag `Tails` below it.
3. The two filter cards (peer_band, metric) appear on the right — keep both.
4. Drag a **Text** object to the very bottom, full width. Paste the footer
   text verbatim. Font size 9, grey.

## 4. Worksheet "Trend — size & capital" (data source: bank_trends)

1. New worksheet, name `Trend — size & capital`.
2. Drag **report_date** to **Columns**; right-click the pill → choose the
   green **continuous Month** (second "Month" entry).
3. Drag **total_assets_bn** to **Rows**; drag **equity_to_assets** to
   **Rows** next to it. Right-click the equity axis → **Dual Axis** is NOT
   wanted — instead leave as two stacked panes (default).
4. Aggregation: right-click each measure pill → **Average** (one row per
   bank-quarter, so AVG = the value).
5. Drag **bank_name** to **Filters** → select `Silicon Valley Bank` → OK →
   Show Filter → Single Value (list). This is the profile selector.

## 5. Worksheet "Trend — funding & margin" (data source: bank_trends)

1. Duplicate the previous sheet (right-click its tab → Duplicate), rename.
2. Swap the Rows measures for: **uninsured_deposit_share**,
   **brokered_deposit_share**, **net_interest_margin_pct** (all Average).
3. The bank_name filter carries over via Apply to Worksheets: on the filter →
   Apply to Worksheets → Selected Worksheets → tick both Trend sheets.

## 6. Dashboard "Bank profile"

1. New dashboard, name `Bank profile`. Size: Automatic.
2. Drag both Trend sheets in, stacked vertically.
3. Keep the bank_name filter card visible, top right, Single Value (list).
4. Same footer Text object at the bottom, verbatim.

## 7. Publish

1. **File → Save to Tableau Public As…** → sign in → name the workbook
   `FDIC Bank Health Monitor — Peer Satellite`.
2. In the browser page that opens after upload: **Edit Details** →
   under **Google Sheets**, enable **Keep this data in sync** (this is the
   daily auto-refresh; it embeds the Google credential server-side).
3. Verify both dashboards render, the filters work, and the footer shows.
4. Send back the workbook's public URL — the site nav and README link to it
   from our side. If the daily sync ever proves flaky, the documented
   fallback is a monthly manual republish of this same workbook.
