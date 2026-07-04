---
title: Bank profile
---

Every bank in the data — active and closed. Search for one, or sort by composite
to see who currently sits furthest from its size peers. Each row opens that bank's
twenty-nine-quarter profile.

```sql directory
with latest_per_bank as (
    select cert, max(report_date) as last_q
    from fdic.fct_bank_quarters group by cert
)
select
    b.bank_name,
    b.city || ', ' || b.state_code as location,
    case when b.is_active then 'Active' else 'Closed' end as status,
    '/bank-profile/' || cast(b.cert as integer) as profile_url,
    f.total_assets / 1e6 as assets_b,
    o.peer_band,
    o.composite_score
from fdic.dim_banks b
join latest_per_bank lpb on lpb.cert = b.cert
left join fdic.fct_bank_quarters f on f.cert = b.cert and f.report_date = lpb.last_q
left join fdic.mart_outlier_flags o on o.cert = b.cert and o.report_date = lpb.last_q
order by b.bank_name
```

<DataTable data={directory} search=true rows=15 link=profile_url>
    <Column id=bank_name title="Institution"/>
    <Column id=location title="Location"/>
    <Column id=status/>
    <Column id=peer_band title="Band"/>
    <Column id=assets_b title="Assets" fmt='"$"#,##0.0"B"'/>
    <Column id=composite_score title="Composite" fmt='#,##0.00'/>
</DataTable>

---

Peer-relative statistics from public filings, never an assessment of any bank's
condition.
