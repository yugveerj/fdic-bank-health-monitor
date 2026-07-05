-- The workhorse table: grain bank x quarter, every metric plus peer band.
-- likely_merger_quarter flags step-change growth (>25% QoQ) so peer statistics
-- and the backtest can distinguish acquisitions from organic growth.
--
-- The semi-join on institutions defines the analytical universe: a handful of
-- insured filers (foreign-bank US branches, a clearing trust) report financials
-- but have no institutions record — they aren't peer-comparable US bank charters
-- and are excluded here, not in ingestion (the raw layer keeps everything).

select
    cast(m.cert as string) || '_' || format_date('%Y%m%d', m.report_date) as bank_quarter_key,
    m.*,
    p.peer_band,
    bm.business_model,
    m.asset_growth_qoq > 0.25                          as likely_merger_quarter
from {{ ref('int_bank_quarter_metrics') }} m
left join {{ ref('int_peer_groups') }} p
    on p.cert = m.cert and p.report_date = m.report_date
left join {{ ref('int_business_models') }} bm
    on bm.cert = m.cert and bm.report_date = m.report_date
where m.cert in (select cert from {{ ref('stg_fdic__institutions') }})
