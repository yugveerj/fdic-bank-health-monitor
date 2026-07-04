# Data verification

How I convinced myself the ingested data is the same data the FDIC publishes.
Last full check: 2026-07-03; the warehouse is current through 2026-Q1
(2026-03-31), and the three-bank table below uses 2025-Q4 values.

## Three-bank cross-check (total assets, total deposits, ROA)

Warehouse values after a from-scratch ingest, compared against independent live API
requests made outside the ingestion code path. Dollar amounts are thousands, as the
FDIC reports them; ROA is percent.

| Bank | CERT | Quarter | Total assets | Total deposits | ROA | API re-check | BankFind UI (assets) |
|---|---|---|---|---|---|---|---|
| JPMorgan Chase Bank, N.A. | 628 | 2025-Q4 | 3,752,662,000 | 2,697,842,000 | 1.3449 | ✅ match | ✅ 20/20 quarters |
| Western Alliance Bank | 57512 | 2025-Q4 | 92,735,703 | 77,639,392 | 1.1029 | ✅ match | ✅ 20/20 quarters |
| Heritage Bank, Inc. | 33119 | 2025-Q4 | 2,094,353 | 1,932,253 | 1.0850 | ✅ match | ✅ 20/20 quarters |

The BankFind UI check is done with the website's own CSV exports rather than by
eyeball: I downloaded each bank's "Quarterly Assets, Past Five Years" file from
https://banks.data.fdic.gov/bankfind-suite/ and compared every row against the
warehouse — **60 of 60 quarterly asset values match exactly** (exports archived
under `docs/verification_exports/`).

<!-- TODO(revise) -->
Deposits and ROA aren't included in that export, so those two columns rest on the
API re-check; spot-checking them once in the UI proper is still on me: ⬜ deposits ⬜ ROA.

## Failed-bank history (the backtest depends on this)

The screen must see 2019–2022 data for banks that no longer exist. Verified in the
warehouse after ingest:

- **Silicon Valley Bank (CERT 24735)** — all 16 quarters, 2019-Q1 through 2022-Q4.
  2022-Q4 total assets: 209,026,000 ($209.0B), exactly matching the `QBFASSET`
  value on its `/failures` record.
- **Signature Bank (CERT 57053)** — 16 quarters through 2022-Q4.
- **First Republic Bank (CERT 59017)** — 17 quarters (it filed 2023-Q1 before
  failing on 2023-05-01).
- **Heartland Tri-State Bank and Citizens Bank (2023)** — 0 quarters, correctly:
  both were far below the $1B scope threshold in every quarter.
- **Silvergate Bank (CERT 27330)** — inactive (`ACTIVE=0`) in institutions but
  absent from `/failures`, as expected for a voluntary liquidation. Anything that
  needs "every closed bank" must use `ACTIVE`, not the failures table.

## Idempotency

Immediately re-running `uv run python -m ingestion.run_all` leaves every table's
row count unchanged (institutions 27,836; financials 28,369; failures 4,115) —
upserts are keyed, not appended.
