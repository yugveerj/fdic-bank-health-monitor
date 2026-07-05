-- Robust peer-relative statistics. Grain: bank x metric x quarter.
-- z = (value - peer_median) / (1.4826 * MAD), winsorized to [-5, 5].
-- MAD = 0 (a degenerate peer distribution) nulls the z rather than dividing.
-- Median/MAD instead of mean/stddev: bank ratios have heavy tails, and a single
-- extreme peer must not be able to mask or manufacture outliers.

with metrics as (
    select * from {{ ref('fct_bank_quarters') }}
),

unpivoted as (
    -- NULL values are excluded by default — that default is what keeps every
    -- downstream median, MAD, and n_screen_metrics count honest
    select *
    from metrics unpivot (
        value for metric in (
            uninsured_deposit_share,
            brokered_deposit_share,
            securities_to_assets,
            asset_growth_3y_cagr,
            asset_growth_yoy,
            deposit_growth_yoy,
            nim_trend_4q,
            equity_to_assets,
            loans_to_deposits,
            roa_pct,
            noncurrent_loans_ratio_pct,
            net_chargeoffs_ratio_pct,
            cost_of_funds_pct,
            efficiency_ratio_pct
        )
    )
),

with_median as (
    select
        *,
        -- exact percentile, never APPROX_QUANTILES: approximation would
        -- silently shift ranks
        percentile_cont(value, 0.5)
            over (partition by metric, report_date, peer_band) as peer_median
    from unpivoted
    where peer_band is not null
),

with_mad as (
    select
        *,
        percentile_cont(abs(value - peer_median), 0.5)
            over (partition by metric, report_date, peer_band) as peer_mad
    from with_median
)

select
    cert,
    report_date,
    peer_band,
    metric,
    value,
    peer_median,
    peer_mad,
    case
        when peer_mad > 0 then
            greatest(-5, least(5, (value - peer_median) / (1.4826 * peer_mad)))
    end as robust_z,
    -- unclamped companion: on zero-inflated metrics (a third of small banks hold
    -- zero brokered deposits) the band MAD is tiny and the +-5 clamp saturates —
    -- drill-downs need the resolution the composite intentionally caps away
    case
        when peer_mad > 0 then (value - peer_median) / (1.4826 * peer_mad)
    end as robust_z_unclamped
from with_mad
