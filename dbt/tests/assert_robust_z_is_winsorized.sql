-- Winsorization guard: robust_z must equal robust_z_unclamped clamped to [-5, 5].
-- The +-5 winsorization is a frozen design choice, but the CI fixture never
-- saturates (its z-scores sit well inside the bound), so nothing there would
-- notice the clamp being removed or its bound changed. This check runs on every
-- build; on the production data — where zero-inflated metrics push the unclamped
-- z past +-5 — it is where a regression to the clamp actually surfaces.
-- Rows returned = failures.

select cert, report_date, metric, robust_z, robust_z_unclamped
from {{ ref('mart_peer_percentiles') }}
where robust_z_unclamped is not null
  and robust_z <> greatest(-5, least(5, robust_z_unclamped))
