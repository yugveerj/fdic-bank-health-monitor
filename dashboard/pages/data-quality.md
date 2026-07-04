---
title: Data quality & lineage
---

How the sausage gets made: sources, tests, lineage, freshness. If you read one
thing on this page, read what the tests caught. The two best bugs in this project
were in the data, not the code.

```sql meta
select built_at, freshest_quarter, bank_quarters, banks, active_banks
from fdic.build_meta
```

<BigValue data={meta} value=freshest_quarter title="Freshest quarter"/>
<BigValue data={meta} value=built_at title="Site built (UTC)"/>
<BigValue data={meta} value=bank_quarters title="Bank-quarters" fmt='#,##0'/>
<BigValue data={meta} value=banks title="Institutions ever in scope"/>

Three counts appear on this site and all of them are right. The homepage
headline is *active* banks reporting in the latest quarter. The status table
below also shows *all* latest-quarter reporters, which adds a handful of
institutions that filed and then closed. The figure above is the widest net:
every institution that has crossed the scope bar since 2019, including banks
that later failed or merged. Each page states which population it shows.

## Status, derived at build time

Every row below is computed from the warehouse or a build artifact when the site
is built. Nothing on this table is typed in by hand.

```sql status
select "check", value, detail from fdic.quality_status
```

<DataTable data={status} rows=12>
    <Column id=check title="Check"/>
    <Column id=value title="Value"/>
    <Column id=detail title="Detail"/>
</DataTable>

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

The repository's [data-quality log](https://github.com/yugveerj/fdic-bank-health-monitor/blob/main/docs/data_quality_log.md)
records real findings as they happen: failure records with NULL certificate
numbers from the 1930s, insured filers that aren't chartered banks, open-bank
assistance events mislabeled as failures, and a z-score saturation effect on
zero-inflated metrics.

![Architecture](https://raw.githubusercontent.com/yugveerj/fdic-bank-health-monitor/main/docs/architecture.png)

