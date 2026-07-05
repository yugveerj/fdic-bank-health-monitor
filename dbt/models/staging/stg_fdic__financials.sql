-- One row per bank-quarter. Types cast, FDIC codes renamed to readable names.
-- Dollar fields arrive in thousands and stay in thousands throughout the project.

select
    cast(CERT as integer)              as cert,
    parse_date('%Y%m%d', REPDTE)       as report_date,
    cast(ASSET as float64)             as total_assets,
    cast(DEP as float64)               as total_deposits,
    cast(EQ as float64)                as equity,
    cast(EQR as float64)               as equity_ratio_pct,
    cast(NETINC as float64)            as net_income_ytd,
    cast(ROA as float64)               as roa_pct,
    cast(ROE as float64)               as roe_pct,
    cast(NIMY as float64)              as net_interest_margin_pct,
    cast(EEFFR as float64)             as efficiency_ratio_pct,
    cast(LNLSNET as float64)           as net_loans_leases,
    cast(SC as float64)                as securities,
    cast(NPERFV as float64)            as nonperforming_assets_ratio_pct,
    cast(NCLNLS as float64)            as noncurrent_loans,
    cast(NCLNLSR as float64)           as noncurrent_loans_ratio_pct,
    cast(BRO as float64)               as brokered_deposits,
    cast(DEPUNA as float64)            as uninsured_deposits_domestic,
    cast(DEPUNINS as float64)          as uninsured_deposits_est,
    cast(NONII as float64)             as noninterest_income_ytd,
    cast(NONIIR as float64)            as noninterest_income_ratio_pct,
    cast(NTLNLS as float64)            as net_chargeoffs_ytd,
    cast(NTLNLSCOR as float64)         as net_chargeoffs_ratio_pct,
    cast(INTEXPY as float64)           as cost_of_funds_pct,
    cast(RBCT1CER as float64)          as cet1_ratio_pct,
    cast(RBCRWAJ as float64)           as total_rbc_ratio_pct,
    cast(RBC1AAJ as float64)           as leverage_ratio_pct
from {{ source('raw_fdic', 'raw_fdic_financials') }}
{% if var('as_of', none) is not none %}
-- backtest freeze: physically exclude everything after the as-of date, so every
-- downstream model provably uses only information available at that time
where parse_date('%Y%m%d', REPDTE) <= date '{{ var("as_of") }}'
{% endif %}
