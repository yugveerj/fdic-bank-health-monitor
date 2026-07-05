-- Weekly H.8 aggregates, typed. FRED serves '.' for missing observations;
-- those become NULL and are dropped. Values are billions of dollars.

select
    series_id,
    series_title,
    cast(obs_date as date)            as obs_date,
    safe_cast(value as float64)       as value_billions
from {{ source('raw_fdic', 'raw_fred_h8') }}
where safe_cast(value as float64) is not null
