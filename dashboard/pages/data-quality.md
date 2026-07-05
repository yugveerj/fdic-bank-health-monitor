---
title: Data quality & lineage
sidebar_position: 6
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

```sql populations
with latest as (select max(report_date) as d from fdic.fct_bank_quarters)
select * from (
    select 1 as ord, count(*) as n, 'Active banks reporting, latest quarter' as population,
           'Homepage headline' as where_used
    from fdic.fct_bank_quarters f join fdic.dim_banks b using (cert)
    where f.report_date = (select d from latest) and b.is_active
    union all
    select 2, count(*), 'All latest-quarter reporters', 'Status table below'
    from fdic.fct_bank_quarters where report_date = (select d from latest)
    union all
    select 3, count(*), 'Institutions ever in scope since 2019', 'Card above'
    from fdic.dim_banks
) order by ord
```

<DataTable data={populations}>
    <Column id=n title="Count" fmt='#,##0'/>
    <Column id=population title="Population"/>
    <Column id=where_used title="Where it appears"/>
</DataTable>

## Status, derived at build time

Every row below is computed from the warehouse or a build artifact when the site
is built. Nothing on this table is typed in by hand.

```sql status
select "check", value, detail,
    case
        when "check" in ('dbt tests', 'Duplicate keys') then 'Integrity'
        when "check" like 'Latest%' then 'Freshness'
        when "check" like 'Banks reporting%' then 'Population'
        else 'Exclusions and oddities'
    end as grp,
    case
        when "check" in ('dbt tests', 'Duplicate keys') then 1
        when "check" like 'Latest%' then 2
        when "check" like 'Banks reporting%' then 3
        else 4
    end as ord
from fdic.quality_status
order by ord, "check"
```

<DataTable data={status} rows=12 groupBy=grp>
    <Column id=check title="Check"/>
    <Column id=value title="Value"/>
    <Column id=detail title="Detail"/>
</DataTable>

## What the tests caught

Real findings, each of which changed the pipeline. The full stories live in the
repository's [data-quality notes](https://github.com/yugveerj/fdic-bank-health-monitor/blob/main/docs/data_quality.md).

- Depression-era failure records carry no certificate number, so failure rows
  are keyed on the API's own ID instead of the obvious natural key.
- A handful of insured filers aren't chartered banks (foreign-bank branches, a
  clearing trust); the exclusion rows above are their receipts.
- The failures feed includes open-bank assistance events; the failure label
  requires an actual FAILURE resolution, and a test enforces it.
- Winsorization saturates on zero-inflated ratios; the composite keeps the
  capped score and the drill-down keeps an unclamped column.
- Step-change growth marks likely acquisitions: the merger flag covers
  <Value data={merger_stats} column=flagged fmt='#,##0'/> bank-quarters across
  <Value data={merger_stats} column=banks fmt='#,##0'/> institutions, so
  acquisition-driven growth is separable from the organic kind.

```sql merger_stats
select count(*) filter (likely_merger_quarter) as flagged,
       count(distinct cert) filter (likely_merger_quarter) as banks
from fdic.fct_bank_quarters
```

## Pipeline

FDIC BankFind Suite API → raw response cache → keyed upserts into the warehouse
(BigQuery) → dbt staging, metrics, and peer-statistics models with
tests on every build → this static site, rebuilt from the warehouse on each
deploy. Quarterly FDIC data lands roughly 60 days after quarter-end; the
scheduled refresh picks up new quarters automatically.

- **[Model lineage and column documentation](https://yugveerj.github.io/fdic-bank-health-monitor/dbt-docs/)** —
  every model, column description, and test, generated from the dbt project on
  each build.
- **[Repository](https://github.com/yugveerj/fdic-bank-health-monitor)** — code,
  test history, and the running log of what the tests caught (README).

![Architecture: FDIC and FRED APIs feed cached Python ingestion into a BigQuery warehouse, dbt builds the models, and Evidence publishes a static site to GitHub Pages, all orchestrated by GitHub Actions](https://raw.githubusercontent.com/yugveerj/fdic-bank-health-monitor/main/docs/architecture.png)



