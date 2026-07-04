-- typed all-NULL schema row when the table is empty: Evidence writes an
-- unreadable parquet for zero rows, and untyped nulls degrade column types
-- (a DATE read back as DOUBLE). Explicit casts keep the schema; every page
-- predicate drops the row. CI always has real rows.
select * from fred_h8
union all
select cast(null as varchar), cast(null as varchar), cast(null as date), cast(null as double)
where (select count(*) from fred_h8) = 0
