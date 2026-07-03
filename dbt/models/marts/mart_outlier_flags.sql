-- Composite outlier score per bank-quarter: the mean of risk-signed robust
-- z-scores across the six screen metrics. Positive = riskier than peers on the
-- screen's definitions. Per-metric contributions are kept for drill-down, and
-- n_screen_metrics shows how much data the composite rests on.
--
-- Risk directions (+ means higher value = riskier):
--   uninsured_deposit_share (+) : runnable funding
--   brokered_deposit_share  (+) : hot, rate-sensitive funding
--   securities_to_assets    (+) : duration / unrealized-loss exposure when rates rise
--   asset_growth_3y_cagr    (+) : rapid balance-sheet expansion
--   nim_trend_4q            (-) : deteriorating margin trend
--   equity_to_assets        (-) : thinner capital cushion

with z as (
    select * from {{ ref('mart_peer_percentiles') }}
),

signed as (
    select
        cert,
        report_date,
        peer_band,
        metric,
        robust_z,
        case metric
            when 'uninsured_deposit_share' then robust_z
            when 'brokered_deposit_share'  then robust_z
            when 'securities_to_assets'    then robust_z
            when 'asset_growth_3y_cagr'    then robust_z
            when 'nim_trend_4q'            then -robust_z
            when 'equity_to_assets'        then -robust_z
        end as risk_signed_z
    from z
    where metric in (
        'uninsured_deposit_share', 'brokered_deposit_share', 'securities_to_assets',
        'asset_growth_3y_cagr', 'nim_trend_4q', 'equity_to_assets'
    )
)

select
    cert,
    report_date,
    peer_band,
    avg(risk_signed_z)                                   as composite_score,
    count(risk_signed_z)                                 as n_screen_metrics,
    max(case when metric = 'uninsured_deposit_share' then risk_signed_z end) as z_uninsured_share,
    max(case when metric = 'brokered_deposit_share'  then risk_signed_z end) as z_brokered_share,
    max(case when metric = 'securities_to_assets'    then risk_signed_z end) as z_securities_share,
    max(case when metric = 'asset_growth_3y_cagr'    then risk_signed_z end) as z_asset_growth_3y,
    max(case when metric = 'nim_trend_4q'            then risk_signed_z end) as z_nim_trend,
    max(case when metric = 'equity_to_assets'        then risk_signed_z end) as z_equity_ratio
from signed
group by cert, report_date, peer_band
