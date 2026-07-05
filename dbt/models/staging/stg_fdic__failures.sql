-- One row per failure event since 1934. Depression-era rows can have NULL cert;
-- the API's ID is the reliable key. Voluntary liquidations are absent by design.

select
    ID                                               as failure_id,
    safe_cast(CERT as integer)                       as cert,
    NAME                                             as bank_name,
    parse_date('%m/%d/%Y', FAILDATE)                 as failure_date,
    cast(FAILYR as integer)                          as failure_year,
    RESTYPE                                          as resolution_type,
    RESTYPE1                                         as resolution_subtype,
    CITYST                                           as city_state,
    cast(QBFASSET as float64)                        as assets_at_failure,
    cast(QBFDEP as float64)                          as deposits_at_failure,
    SAVR                                             as insurance_fund,
    CHCLASS1                                         as charter_class
from {{ source('raw_fdic', 'raw_fdic_failures') }}
