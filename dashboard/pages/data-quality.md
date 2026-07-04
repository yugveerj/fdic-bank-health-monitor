---
title: Data quality & lineage
---

<!-- TODO(revise): intro in my words. -->

Where this data comes from, how fresh it is, and what stands between the API and
the charts.

```sql meta
select built_at, freshest_quarter, bank_quarters, banks, active_banks
from fdic.build_meta
```

<BigValue data={meta} value=freshest_quarter title="Freshest quarter"/>
<BigValue data={meta} value=built_at title="Site built (UTC)"/>
<BigValue data={meta} value=bank_quarters title="Bank-quarters" fmt='#,##0'/>
<BigValue data={meta} value=banks title="Institutions"/>

## Pipeline

FDIC BankFind Suite API → raw response cache → keyed upserts into the warehouse
(DuckDB / MotherDuck) → dbt staging, metrics, and peer-statistics models with
tests on every build → this static site, rebuilt from the warehouse on each
deploy. Quarterly FDIC data lands roughly 60 days after quarter-end; the
scheduled refresh picks up new quarters automatically.

- **[Model lineage and column documentation](https://yugveerj.github.io/fdic-bank-health-monitor/dbt-docs/)** —
  every model, column description, and test, generated from the dbt project on
  each build.
- **[Repository](https://github.com/yugveerj/fdic-bank-health-monitor)** — code,
  test history, and the running log of what the tests caught (README).

## Notable things the tests caught

The README's "What the tests caught" section documents real data-quality findings
as they happen — including failure records with NULL certificate numbers from the
1930s, insured filers that aren't chartered banks, open-bank assistance events
mislabeled as failures, and a z-score saturation effect on zero-inflated metrics.

![Architecture](https://raw.githubusercontent.com/yugveerj/fdic-bank-health-monitor/main/docs/architecture.png)

---

_Peer-relative statistics, not assessments of safety or soundness._
