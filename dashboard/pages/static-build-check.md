---
title: Static build check (scratch)
---

<!-- Scratch page — replaced when the real dashboard pages land.
     Purpose: prove that an input component driving a parameterized query
     works in the static production build (GitHub Pages has no server).
     Same interaction pattern the bank-profile page will need
     (bank selector -> per-bank trends). -->

```sql categories
select category
from needful_things.orders
group by category
order by category
```

<Dropdown data={categories} name=check_category value=category title="Category">
    <DropdownOption value="%" valueLabel="All Categories"/>
</Dropdown>

```sql filtered_sales
select
    category,
    count(*) as order_count,
    sum(sales) as total_sales
from needful_things.orders
where category like '${inputs.check_category.value}'
group by category
order by total_sales desc
```

<DataTable data={filtered_sales}>
    <Column id=category/>
    <Column id=order_count/>
    <Column id=total_sales fmt=usd/>
</DataTable>

If changing the dropdown re-filters the table on a statically-served build,
the GitHub Pages architecture is proven for interactive pages.
