# Data-quality log

Real findings in the data, newest first. Bank data will not be clean, and the
tests exist to prove it.

- **2026-07-03** — "Failed" banks that are alive and enormous. While
  stress-testing the failure labels I found five currently active banks marked
  as failed, Citibank and Bank of America among them. The FDIC endpoint is
  really "failures *and assistance*": it includes open-bank ASSISTANCE events
  (Citibank 2008, FirstBank Puerto Rico 1981) alongside true failures. My
  `is_failed` flag now requires `resolution_type = 'FAILURE'`. Without this,
  the 2023 backtest labels would have broken, and so would the rule that
  operating banks are never described as failed.

- **2026-07-03** — A z-score cap that erased the differences it was built to
  show. I winsorize peer z-scores at ±5 so a single wild value can't dominate
  the composite. That's standard practice, but I checked what it does on my
  actual data: 16% of brokered-deposit-share observations sit at exactly +5,
  because a third of $1–10B banks hold zero brokered deposits, which crushes
  the band's MAD and makes anything above ~18% share saturate. A 20%-brokered
  bank and a 99%-brokered bank were scoring identically. The composite keeps
  the cap (stability is the point). I added an unclamped z column so
  drill-downs keep their resolution, and the saturation is documented as a
  known limitation of the method.

- **2026-07-03** — Insured filers that aren't banks. A dbt relationship test
  failed on 123 bank-quarters whose certificate has no institutions record.
  They're real: Bank of China's US branch, Depository Trust Co, and four other
  insured non-bank filers report financials but aren't chartered US banks. The
  analytical universe is now defined as "institutions in the FDIC registry".
  The raw layer keeps everything; the fact model applies the rule.

- **2026-07-03** — NULL certificate numbers in Depression-era failure records.
  My upsert guard rejects batches with duplicate keys, and the very first
  `/failures` load tripped it: 53 collisions on `(CERT, FAILDATE)`. The cause
  is 1930s failure records with no certificate number. Six different banks all
  "failed" on 1936-12-21 with `CERT` null. The fix: key failure records on the
  API's own `ID` field, which is unique on all 4,115 rows. The lesson I'm
  keeping: never assume a natural key holds across ninety years of records.
