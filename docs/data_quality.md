# Data quality

This file answers one question: why should anyone trust the numbers this
project publishes? It has two halves. The first describes how I checked that
the data in my warehouse is the same data the FDIC publishes. The second is a
running log of the things my tests caught, because bank data is messy and the
catches are half the value of testing it.

## Verifying the ingested data

The pipeline pulls from the FDIC's public API, and the obvious failure mode is
that some bug of mine quietly corrupts values on the way in. So after the first
full ingest I picked three banks of very different sizes and compared what my
warehouse holds against what the FDIC serves through requests made completely
outside my ingestion code. I checked total assets, total deposits, and return
on assets for each, using the 2025-Q4 filings. All nine values matched exactly.
The last full check ran on 2026-07-03, at which point the warehouse was
current through 2026-Q1.

| Bank | CERT | Quarter | Total assets | Total deposits | ROA | API re-check | BankFind UI (assets) |
|---|---|---|---|---|---|---|---|
| JPMorgan Chase Bank, N.A. | 628 | 2025-Q4 | 3,752,662,000 | 2,697,842,000 | 1.3449 | match | 20/20 quarters |
| Western Alliance Bank | 57512 | 2025-Q4 | 92,735,703 | 77,639,392 | 1.1029 | match | 20/20 quarters |
| Heritage Bank, Inc. | 33119 | 2025-Q4 | 2,094,353 | 1,932,253 | 1.0850 | match | 20/20 quarters |

Dollar amounts are in thousands because that is how the FDIC reports them, and
ROA is a percentage.

The last column deserves a word. Rather than eyeballing the BankFind website,
I downloaded each bank's "Quarterly Assets, Past Five Years" CSV from the site
itself and compared every row against the warehouse. Sixty asset values across
twenty quarters and three banks, and all sixty matched. The downloaded files
are archived under `docs/verification_exports/` so anyone can repeat the
comparison. The export only covers assets, so deposits and ROA rest on the API
re-check for now; spot-checking those two in the BankFind interface is still on
my list: ⬜ deposits ⬜ ROA.

The check that mattered most was different. My 2023 backtest depends on the
history of banks that no longer exist, and if the FDIC dropped financials for
closed institutions the whole exercise would be impossible. It doesn't.
Silicon Valley Bank (CERT 24735) has all sixteen quarters from 2019-Q1 through
2022-Q4 in my warehouse, and its final reported assets of 209,026,000 thousand
match the QBFASSET value on its failure record to the dollar. Signature Bank
has its sixteen quarters, First Republic seventeen because it filed once more
in early 2023 before failing that May. The two 2023 failures below my one
billion dollar scope line, Heartland Tri-State and Citizens Bank of Sac City,
correctly have no quarters at all. Silvergate Bank shows up as inactive in the
institutions data but is absent from the failures feed, which is right, because
it wound itself down voluntarily. Anything that needs a list of every closed
bank has to use the active flag, not the failures table.

One more property worth stating because everything else relies on it: the
ingestion is idempotent. Running the full ingest twice in a row leaves every
table's row count unchanged (27,836 institutions, 28,369 bank-quarters, 4,115
failure records at last full check). Loads are keyed upserts, not appends, so
a re-run can update rows but never duplicate them.

## What the tests caught

Real findings, newest first. Each one changed the pipeline in some way, and
each is the kind of thing that would have quietly poisoned results if nothing
had been watching.

**Failed banks that are alive and enormous** (July 2026). While stress-testing
the failure labels I found five currently active banks marked as failed,
Citibank and Bank of America among them. The FDIC endpoint is really "failures
and assistance" in one feed: it includes open-bank assistance events, like
Citibank's in 2008 and FirstBank Puerto Rico's in 1981, alongside true
failures. My failure flag now requires an actual FAILURE resolution type, and
a test enforces that. Without the fix, the 2023 backtest labels would have
broken, and so would my rule that operating banks are never described as
failed.

**A z-score cap that erased the differences it was built to show** (July 2026).
I winsorize peer z-scores at plus or minus five so a single wild value can't
dominate the composite. That's standard practice, but I checked what it does
on my actual data: 16% of brokered-deposit-share observations sit at exactly
+5. The cause is that a third of the banks in the one-to-ten-billion band hold
zero brokered deposits, which crushes the band's median absolute deviation and
makes anything above roughly an 18% share saturate. A bank with 20% brokered
funding and a bank with 99% were scoring identically. The composite keeps the
cap, since stability is the point, but I added an unclamped column so
drill-downs keep their resolution, and the saturation is documented as a known
limitation rather than discovered later.

**Insured filers that aren't banks** (July 2026). A dbt relationship test
failed on 123 bank-quarters whose certificate number has no matching record in
the institutions registry. They turned out to be real filers but not chartered
US banks: Bank of China's US branch, Depository Trust Company, and four other
insured non-bank institutions that report financials without being the kind of
bank this project compares. The analytical universe is now defined as
institutions in the FDIC registry. The raw layer keeps everything; the fact
model applies the rule.

**Null certificate numbers in Depression-era failure records** (July 2026). My
upsert guard rejects any batch with duplicate keys, and the very first load of
the failures feed tripped it: 53 collisions on the certificate-plus-date key.
The cause was 1930s failure records with no certificate number at all, six
different banks all "failing" on December 21, 1936 with a null CERT. The fix
keys failure records on the API's own ID field, which is unique across all
4,115 rows. The lesson I kept: never assume a natural key holds across ninety
years of records.

There is also a flag rather than a fix worth mentioning here. Step-change
growth, more than 25% in a single quarter, almost always marks an acquisition
rather than organic growth, and the fact table carries a merger flag so the
two can be told apart. The 2023 case study leans on it when separating
acquisition-driven growth from the organic deposit-inflow kind that
characterized Silicon Valley Bank.
