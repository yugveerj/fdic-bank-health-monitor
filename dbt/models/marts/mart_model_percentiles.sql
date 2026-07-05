-- Peer statistics computed within business-model groups instead of size bands.
-- Same robust method as mart_peer_percentiles; a context layer for drill-downs.
-- The screen's composite does not read this table.

with metrics as (
    select f.*, m.business_model
    from {{ ref('fct_bank_quarters') }} f
    join {{ ref('int_business_models') }} m
      on m.cert = f.cert and m.report_date = f.report_date
),

unpivoted as (
    -- NULL values are excluded by default, same as mart_peer_percentiles
    select *
    from metrics unpivot (
        value for metric in (
            uninsured_deposit_share,
            brokered_deposit_share,
            securities_to_assets,
            asset_growth_3y_cagr,
            nim_trend_4q,
            equity_to_assets,
            loans_to_deposits,
            roa_pct,
            noncurrent_loans_ratio_pct,
            efficiency_ratio_pct
        )
    )
),

with_median as (
    select
        *,
        -- exact percentile, never APPROX_QUANTILES
        percentile_cont(value, 0.5)
            over (partition by metric, report_date, business_model) as model_median
    from unpivoted
),

with_mad as (
    select
        *,
        percentile_cont(abs(value - model_median), 0.5)
            over (partition by metric, report_date, business_model) as model_mad
    from with_median
)

select
    cert,
    report_date,
    business_model,
    metric,
    value,
    model_median,
    model_mad,
    case
        when model_mad > 0 then
            greatest(-5, least(5, (value - model_median) / (1.4826 * model_mad)))
    end as robust_z
from with_mad
