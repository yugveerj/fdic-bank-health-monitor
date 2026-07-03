# Backtest methodology

<!-- TODO(revise) -->
_Narrative (freeze design, screen construction, honest caveats) comes when the
backtest is built. This file starts with the metric → source-field map so every
number in the pipeline is traceable to an official FDIC field code._

## Metric sources

Every field code below comes from the FDIC's official dictionaries (saved under
`docs/fdic_*_properties.yaml`) and was confirmed against a live `/financials`
response on 2026-07-03. Dollar levels are thousands; ratio fields are percent.

| Metric | Source field(s) | Notes |
|---|---|---|
| Total assets | `ASSET` | |
| Total deposits | `DEP` | |
| Net loans & leases | `LNLSNET` | |
| Loans / deposits | derived: `LNLSNET / DEP` | computed in dbt |
| ROA | `ROA` | |
| ROE | `ROE` | |
| Net interest margin | `NIMY` | 4-quarter trend slope computed in dbt |
| Efficiency ratio | `EEFFR` | |
| Noninterest income share | `NONIIR` (+ `NONII` level) | |
| Equity / assets | `EQR` (+ `EQ` level) | |
| Risk-based capital | `RBCRWAJ` (total), `RBCT1CER` (CET1), `RBC1AAJ` (leverage) | |
| Brokered-deposit share | derived: `BRO / DEP` | `BRO` is the level, thousands |
| Uninsured-deposit share | derived: `DEPUNINS / DEP` | provided by FDIC as an estimate; `DEPUNA` is the domestic-offices variant — both ingested, definitional choice documented when the screen is built |
| Cost of funds | `INTEXPY` | interest expense / earning assets |
| Noncurrent loans ratio | `NCLNLSR` (+ `NCLNLS` level) | |
| Net charge-offs ratio | `NTLNLSCOR` (+ `NTLNLS` level) | `NTLNLS` is year-to-date |
| Nonperforming assets / assets | `NPERFV` | |
| Securities / assets | derived: `SC / ASSET` | |
| YoY / 3-yr asset growth | derived from `ASSET` | computed in dbt |
| YoY deposit growth | derived from `DEP` | computed in dbt |

## Screen metrics and risk directions

<!-- TODO(revise) -->
_Filled in when the screen is implemented, with a one-sentence rationale per
direction._
