-- One row per institution, active and inactive. ENDEFYMD arrives as MM/DD/YYYY.

select
    cast(CERT as integer)                            as cert,
    NAME                                             as bank_name,
    CITY                                             as city,
    STALP                                            as state_code,
    STNAME                                           as state_name,
    ZIP                                              as zip,
    cast(ACTIVE as integer) = 1                      as is_active,
    BKCLASS                                          as bank_class,
    try_cast(strptime(ESTYMD, '%m/%d/%Y') as date)   as established_date,
    try_cast(strptime(ENDEFYMD, '%m/%d/%Y') as date) as end_of_existence_date,
    cast(CHANGEC1 as integer)                        as latest_change_code,
    cast(FED_RSSD as integer)                        as fed_rssd_id,
    WEBADDR                                          as website,
    cast(ASSET as double)                            as current_assets,
    cast(DEP as double)                              as current_deposits
from {{ source('raw_fdic', 'raw_fdic_institutions') }}
