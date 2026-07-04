# Backlog

Queued ideas, roughly in the order I'd take them on.

## Open

- If the quarterly alert should reach me off GitHub, wire the notify job to Slack
  or email instead of (or alongside) the repo issue it opens now.
- Screen-reader access to the charts themselves: the canvas charts aren't
  readable, and only the analytical pages currently back them with data tables.
  A per-chart data-table toggle would close that on the profile pages too.

## Assessed, not doing

- Deep-linkable per-bank profile pages. I tried Evidence templated pages
  (`/bank-profile/[cert]`, one per bank): the build works, but it emits ~15,000
  files (a prerendered query result per page per chart), and the GitHub Pages
  deploy can't sync that many — it fails at "syncing_files". Reverted to the
  single searchable/dropdown profile (~270 files, deploys clean). Real
  deep-links would need a host that handles the file count (Cloudflare Pages /
  Netlify) or Evidence dropping per-page query prerendering.
- Folding the metric display-name maps into a dbt seed. On inspection the only
  real duplication is a four-row business-model map across two pages; a seed plus
  its export and per-page joins would add more plumbing than it removes. Left as
  inline maps on purpose.

## Recently shipped

Workflow:

- The outlier screen shows the biggest quarter-over-quarter composite moves in a
  band, not just the current level.
- The peer explorer can highlight a chosen bank on the distribution.

Analysis:

- The profile page charts a bank's composite over time, tying it back to the
  screen.
- The outlier screen shows how correlated the six screen metrics are — honest
  about overlap; the composite stays unweighted.

Operational:

- The weekly job now checks FRED feed freshness and flags a stale feed instead of
  deploying old H.8 numbers silently.
- A new FDIC quarter opens a repo issue announcing it, rather than redeploying in
  silence.
- Accessibility pass: the dark theme already clears WCAG AA (~12:1 text
  contrast, clean heading order, focusable controls); gave the architecture
  image real alt text.

Earlier polish:

- Human-readable metric and business-model labels everywhere.
- Median / 10th / 90th reference lines on the peer-explorer histogram.
- A data-vintage line on the landing page.
- Architecture diagram: model count corrected to twelve, and the CI bullet now
  says pull requests build against a committed sample, not the warehouse.
