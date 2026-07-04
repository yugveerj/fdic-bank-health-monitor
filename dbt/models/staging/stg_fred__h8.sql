-- Weekly H.8 aggregates, typed. FRED serves '.' for missing observations;
-- those become NULL and are dropped. Values are billions of dollars.

select
    series_id,
    series_title,
    obs_date::date                    as obs_date,
    try_cast(value as double)         as value_billions
from {{ source('raw_fdic', 'raw_fred_h8') }}
where try_cast(value as double) is not null
