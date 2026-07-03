-- Grain: bank x quarter. Derived ratios, calendar-true growth rates, NIM trend.
--
-- Growth joins use a quarter index (year*4 + quarter), NOT row lags and NOT date
-- arithmetic: the >$1B scope filter is per-quarter, so a bank can have gaps in its
-- history (row lags would compare wrong quarters), and quarter-end date arithmetic
-- is off-by-a-day for Q2 (June 30 - 3 months = March 30, not March 31).
--
-- The NIM slope regresses on the quarter index over the trailing 4 observations
-- and is nulled unless all 4 quarters are present.

with financials as (
    select
        *,
        year(report_date) * 4 + quarter(report_date) as quarter_index
    from {{ ref('stg_fdic__financials') }}
),

with_trend as (
    select
        *,
        regr_slope(net_interest_margin_pct, quarter_index) over trailing_4q as nim_slope_raw,
        count(net_interest_margin_pct) over trailing_4q                     as nim_obs_4q
    from financials
    window trailing_4q as (
        partition by cert
        order by quarter_index
        range between 3 preceding and current row
    )
)

select
    f.cert,
    f.report_date,
    f.quarter_index,
    f.total_assets,
    f.total_deposits,
    f.equity,
    f.net_loans_leases,
    f.securities,
    f.brokered_deposits,
    f.uninsured_deposits_est,
    f.roa_pct,
    f.roe_pct,
    f.net_interest_margin_pct,
    f.efficiency_ratio_pct,
    f.noninterest_income_ratio_pct,
    f.cost_of_funds_pct,
    f.noncurrent_loans_ratio_pct,
    f.net_chargeoffs_ratio_pct,
    f.nonperforming_assets_ratio_pct,
    f.cet1_ratio_pct,
    f.total_rbc_ratio_pct,
    f.leverage_ratio_pct,

    f.equity / nullif(f.total_assets, 0)                   as equity_to_assets,
    f.net_loans_leases / nullif(f.total_deposits, 0)       as loans_to_deposits,
    f.securities / nullif(f.total_assets, 0)               as securities_to_assets,
    f.brokered_deposits / nullif(f.total_deposits, 0)      as brokered_deposit_share,
    f.uninsured_deposits_est / nullif(f.total_deposits, 0) as uninsured_deposit_share,

    f.total_assets / nullif(prior_1q.total_assets, 0) - 1  as asset_growth_qoq,
    f.total_assets / nullif(prior_1y.total_assets, 0) - 1  as asset_growth_yoy,
    pow(f.total_assets / nullif(prior_3y.total_assets, 0), 1.0 / 3) - 1
                                                            as asset_growth_3y_cagr,
    f.total_deposits / nullif(prior_1y.total_deposits, 0) - 1
                                                            as deposit_growth_yoy,

    case when f.nim_obs_4q = 4 then f.nim_slope_raw end     as nim_trend_4q

from with_trend f
left join financials prior_1q
    on prior_1q.cert = f.cert and prior_1q.quarter_index = f.quarter_index - 1
left join financials prior_1y
    on prior_1y.cert = f.cert and prior_1y.quarter_index = f.quarter_index - 4
left join financials prior_3y
    on prior_3y.cert = f.cert and prior_3y.quarter_index = f.quarter_index - 12
