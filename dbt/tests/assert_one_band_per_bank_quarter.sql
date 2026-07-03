-- Every in-scope bank-quarter must land in exactly one peer band: a null band
-- would silently drop the bank from all peer statistics.

select cert, report_date, total_assets, peer_band
from {{ ref('fct_bank_quarters') }}
where total_assets >= 1_000_000
  and peer_band is null
