-- Business-model classification per bank-quarter. Rule-based on purpose: every
-- assignment is explainable from three reported ratios, and thresholds are
-- fixed (not fitted). First matching rule wins; order is most-structural-first.
--
--   fee_custody         loans/assets < 0.20   barely lends: trust, custody, fee banks
--   wholesale_funded    brokered/dep > 0.25   funding bought, not gathered
--   securities_focused  securities/assets > 0.50
--   traditional_lender  everyone else (~95% of banks)
--
-- This is a CONTEXT layer. The outlier composite and the 2023 backtest stay on
-- size bands exactly as published.

select
    cert,
    report_date,
    case
        when net_loans_leases / nullif(total_assets, 0) < 0.20 then 'fee_custody'
        when brokered_deposit_share > 0.25                     then 'wholesale_funded'
        when securities_to_assets > 0.50                       then 'securities_focused'
        else 'traditional_lender'
    end as business_model
from {{ ref('int_bank_quarter_metrics') }}
