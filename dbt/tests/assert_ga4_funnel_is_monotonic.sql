-- Funnel stages must nest per week: sessions >= with_view >= with_cart >=
-- with_purchase. The closed-funnel construction should force this; a
-- violation means the model reverted to open per-stage countifs (which the
-- sample's early add_to_cart gap breaks) or the session join fanned out.
-- Rows returned = failures.

select week, sessions, sessions_with_view, sessions_with_cart, sessions_with_purchase
from {{ ref('mart_ga4_sample_funnel') }}
where sessions < sessions_with_view
   or sessions_with_view < sessions_with_cart
   or sessions_with_cart < sessions_with_purchase
