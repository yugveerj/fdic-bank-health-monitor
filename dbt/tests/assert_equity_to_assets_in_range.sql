-- Accepted-range check: equity/assets outside [-0.5, 1] means either broken
-- ingestion or a unit mistake, not a real bank. Rows returned = failures.

select cert, report_date, equity_to_assets
from {{ ref('fct_bank_quarters') }}
where equity_to_assets is not null
  and (equity_to_assets < -0.5 or equity_to_assets > 1)
