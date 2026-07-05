-- retention_pct is a share of the cohort: outside [0, 1] means the activity
-- join fanned out. Week 0 below 1.0 means cohort assignment and activity
-- disagree about a user's first week — by construction every cohort member is
-- active in week 0. Rows returned = failures.

select cohort_week, week_number, cohort_size, active_users, retention_pct
from {{ ref('mart_ga4_sample_retention') }}
where retention_pct < 0
   or retention_pct > 1
   or (week_number = 0 and retention_pct != 1.0)
