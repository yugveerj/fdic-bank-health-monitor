-- One row per bank-quarter. Types cast, FDIC codes renamed to readable names.
-- Dollar fields arrive in thousands and stay in thousands throughout the project.

select
    cast(CERT as integer)              as cert,
    strptime(REPDTE, '%Y%m%d')::date   as report_date,
    cast(ASSET as double)              as total_assets,
    cast(DEP as double)                as total_deposits,
    cast(EQ as double)                 as equity,
    cast(EQR as double)                as equity_ratio_pct,
    cast(NETINC as double)             as net_income_ytd,
    cast(ROA as double)                as roa_pct,
    cast(ROE as double)                as roe_pct,
    cast(NIMY as double)               as net_interest_margin_pct,
    cast(EEFFR as double)              as efficiency_ratio_pct,
    cast(LNLSNET as double)            as net_loans_leases,
    cast(SC as double)                 as securities,
    cast(NPERFV as double)             as nonperforming_assets_ratio_pct,
    cast(NCLNLS as double)             as noncurrent_loans,
    cast(NCLNLSR as double)            as noncurrent_loans_ratio_pct,
    cast(BRO as double)                as brokered_deposits,
    cast(DEPUNA as double)             as uninsured_deposits_domestic,
    cast(DEPUNINS as double)           as uninsured_deposits_est,
    cast(NONII as double)              as noninterest_income_ytd,
    cast(NONIIR as double)             as noninterest_income_ratio_pct,
    cast(NTLNLS as double)             as net_chargeoffs_ytd,
    cast(NTLNLSCOR as double)          as net_chargeoffs_ratio_pct,
    cast(INTEXPY as double)            as cost_of_funds_pct,
    cast(RBCT1CER as double)           as cet1_ratio_pct,
    cast(RBCRWAJ as double)            as total_rbc_ratio_pct,
    cast(RBC1AAJ as double)            as leverage_ratio_pct
from {{ source('raw_fdic', 'raw_fdic_financials') }}
{% if var('as_of', none) is not none %}
-- backtest freeze: physically exclude everything after the as-of date, so every
-- downstream model provably uses only information available at that time
where strptime(REPDTE, '%Y%m%d')::date <= '{{ var("as_of") }}'::date
{% endif %}
