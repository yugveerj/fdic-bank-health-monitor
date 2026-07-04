# Backlog

Queued ideas, roughly in the order I'd take them on.

- Business-model peer groups. Size-only bands put SVB next to JPMorgan; grouping
  by funding profile or loan mix would sharpen every comparison. First upgrade
  I'd make, and the biggest.
- A dbt source-freshness gate on the weekly job, so a quietly stale FRED feed
  turns a run yellow instead of nothing.
- Per-bank screen history: a small chart on the profile page showing a bank's
  composite over time, not just the current quarter.
- Architecture diagram wording: the CI bullet should say pull requests build
  against a committed sample, not the warehouse (fix with the planned redraw).
- Alerting on the quarterly trigger: a notification when a new FDIC quarter
  actually lands, not just the silent refresh.
