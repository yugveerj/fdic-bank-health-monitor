# Backlog

Queued ideas, roughly in the order I'd take them on.

## Workflow — make the four pages feel like one tool

- Link the outlier-screen ranked table straight to each bank's profile, so the
  "open the profile for trend context" step is one click instead of a re-search.
  (Needs the profile's bank selector to accept a cert from the URL — worth a
  short spike first.)
- Show movement: a quarter-over-quarter composite delta, and a short "biggest
  movers" list, since the analyst steps already tell you to watch for it.
- Let a reader drop a chosen bank onto the peer-explorer and outlier
  distributions to see exactly where it sits.

## Analysis

- Per-bank screen history: a small chart on the profile page showing a bank's
  composite over time, not just the current quarter.
- A methodology panel showing how correlated the six screen metrics are — honest
  about where they overlap. Context only; the composite stays as it is.

## Operational

- A dbt source-freshness gate on the weekly job, so a quietly stale FRED feed
  turns a run yellow instead of nothing.
- Alerting on the quarterly trigger: a notification when a new FDIC quarter
  actually lands, not just the silent refresh.
- An accessibility pass — dark-theme contrast, chart alt text, keyboard-friendly
  dropdowns — checked against WCAG AA.
- Housekeeping: fold the metric display-name map into one place (a dbt seed)
  instead of the two page-level CASE blocks it lives in now.

## Recently shipped (dashboard polish pass)

- Human-readable metric and business-model labels everywhere — the dropdowns,
  chart titles, and legends read "Return on assets", not `roa_pct`.
- Median / 10th / 90th reference lines drawn on the peer-explorer histogram,
  not just listed in the table beside it.
- A data-vintage line on the landing page: which quarter the data runs through,
  how many bank-quarters, and when the site was last rebuilt.
- Architecture diagram: the model count now reads twelve, and the CI bullet says
  pull requests build against a committed sample rather than the warehouse.
