-- One row per institution that appears in the financials scope, with failure
-- attributes joined on. is_failed means an actual FAILURE resolution: the FDIC
-- endpoint also carries open-bank ASSISTANCE records (e.g. Citibank 2008), which
-- must not mark a living bank as failed. Voluntary closures show
-- is_active = false with no failure row (e.g. Silvergate).

with in_scope as (
    select distinct cert from {{ ref('stg_fdic__financials') }}
),

failures as (
    select
        cert,
        failure_date,
        resolution_type,
        assets_at_failure
    from {{ ref('stg_fdic__failures') }}
    where cert is not null
      and resolution_type = 'FAILURE'
    qualify row_number() over (partition by cert order by failure_date desc) = 1
)

select
    i.cert,
    i.bank_name,
    i.city,
    i.state_code,
    i.state_name,
    i.bank_class,
    i.is_active,
    i.established_date,
    i.end_of_existence_date,
    i.website,
    i.current_assets,
    i.current_deposits,
    f.cert is not null      as is_failed,
    f.failure_date,
    f.resolution_type,
    f.assets_at_failure
from {{ ref('stg_fdic__institutions') }} i
join in_scope using (cert)
left join failures f using (cert)
