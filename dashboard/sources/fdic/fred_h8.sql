-- typed all-NULL schema row when the table is empty: Evidence writes an
-- unreadable parquet for zero rows, and untyped nulls degrade column types
-- (a DATE read back as DOUBLE). Explicit casts keep the schema; every page
-- predicate drops the row. CI always has real rows.
select * from analytics.stg_fred__h8
union all
select cast(null as string), cast(null as string), cast(null as date), cast(null as float64)
from (select 1)
where (select count(*) from analytics.stg_fred__h8) = 0
