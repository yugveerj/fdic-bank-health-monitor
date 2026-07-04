-- all-NULL schema row when the table is empty: Evidence writes an unreadable
-- parquet for zero-row extractions; a null row keeps the file valid and every
-- page predicate (obs_date >= ...) drops it. CI always has real rows.
select * from fred_h8
union all
select null, null, null, null where (select count(*) from fred_h8) = 0
