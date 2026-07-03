-- The workhorse table: grain bank x quarter, every metric plus peer band.
-- likely_merger_quarter flags step-change growth (>25% QoQ) so peer statistics
-- and the backtest can distinguish acquisitions from organic growth.
--
-- The semi-join on institutions defines the analytical universe: a handful of
-- insured filers (foreign-bank US branches, a clearing trust) report financials
-- but have no institutions record — they aren't peer-comparable US bank charters
-- and are excluded here, not in ingestion (the raw layer keeps everything).

select
    m.cert || '_' || strftime(m.report_date, '%Y%m%d') as bank_quarter_key,
    m.*,
    p.peer_band,
    m.asset_growth_qoq > 0.25                          as likely_merger_quarter
from {{ ref('int_bank_quarter_metrics') }} m
left join {{ ref('int_peer_groups') }} p
    on p.cert = m.cert and p.report_date = m.report_date
where m.cert in (select cert from {{ ref('stg_fdic__institutions') }})
