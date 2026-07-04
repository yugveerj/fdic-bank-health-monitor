# FRED H.8 series selection

The dashboard's weekly sector view runs on four series from the Federal
Reserve's H.8 release, **Assets and Liabilities of Commercial Banks in the
United States** (FRED release id 22, selected from the official release page
on 2026-07-03). All four are the *Billions of U.S. Dollars, Weekly, Seasonally
Adjusted* variants. Weekly data reaches back to 1973 and updates a few days
after each H.8 publication.

| Series ID | Official title | Why it's here |
|---|---|---|
| `DPSACBW027SBOG` | Deposits, All Commercial Banks | The system-wide funding base — the weekly pulse behind the quarterly deposit stories on the dashboard. |
| `TOTBKCR` | Bank Credit, All Commercial Banks | Total credit extended by banks, the broadest weekly activity measure in the release. |
| `TOTCI` | Commercial and Industrial Loans, All Commercial Banks | The classic business-lending cycle indicator. |
| `TLAACBW027SBOG` | Total Assets, All Commercial Banks | System-level balance-sheet size, matching the dashboard's quarterly sector view. |

This file is documentation, not configuration, and the ingestion code does not
trust it alone: on every run it fetches each series' metadata from the FRED
API and fails loudly if an ID no longer resolves or its official title has
drifted from what's recorded here. If FRED renames or retires a series, the
weekly job breaks visibly instead of charting the wrong thing.
