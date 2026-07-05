-- FAILURE-vs-ASSISTANCE guard. The FDIC failures endpoint also carries open-bank
-- ASSISTANCE records (e.g. Bank of America and Citibank, 2009), and is_failed must
-- stay reserved for actual FAILURE resolutions. Any bank whose failure records are
-- all non-FAILURE yet is flagged is_failed means dim_banks lost its resolution_type
-- filter. Vacuous on the CI fixture (its failure rows are all FAILURE) but exercised
-- on the production build, where five active >$1B banks carry assistance events.
-- Rows returned = failures.

with assistance_only as (
    select cert
    from {{ ref('stg_fdic__failures') }}
    where cert is not null
    group by cert
    having countif(resolution_type = 'FAILURE') = 0
)

select d.cert, d.bank_name
from {{ ref('dim_banks') }} d
join assistance_only using (cert)
where d.is_failed
