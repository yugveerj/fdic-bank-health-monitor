-- Peer bands recomputed each quarter from that quarter's assets (thousands):
-- $1-10B, $10-100B, >$100B. A bank moves bands as it grows or shrinks.

select
    cert,
    report_date,
    case
        when total_assets >= 100_000_000 then '>$100B'
        when total_assets >= 10_000_000  then '$10B-$100B'
        when total_assets >= 1_000_000   then '$1B-$10B'
    end as peer_band
from {{ ref('stg_fdic__financials') }}
