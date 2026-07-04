# FRED H.8 series selection

Selected from the official release page — **H.8 Assets and Liabilities of
Commercial Banks in the United States** (fred.stlouisfed.org, release id 22,
retrieved 2026-07-03). All four are the *Billions of U.S. Dollars, Weekly,
Seasonally Adjusted* variants; weekly data reaches back to 1973 and updates a
few days after each H.8 publication.

| Series ID | Official title | Why it's here |
|---|---|---|
| `DPSACBW027SBOG` | Deposits, All Commercial Banks | The system-wide funding base — the weekly pulse behind the quarterly deposit stories on the dashboard. |
| `TOTBKCR` | Bank Credit, All Commercial Banks | Total credit extended by banks — the broadest weekly activity measure in the release. |
| `TOTCI` | Commercial and Industrial Loans, All Commercial Banks | The classic business-lending cycle indicator. |
| `TLAACBW027SBOG` | Total Assets, All Commercial Banks | System-level balance-sheet size, matching the dashboard's quarterly sector view. |

The ingestion code does not trust this file alone: on every run it fetches each
series' metadata from the FRED API and fails loudly if the ID no longer resolves
or its official title drifts from what is recorded here.
