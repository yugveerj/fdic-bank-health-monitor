# Backlog

Ideas queued, ideas rejected, and ideas shipped. Roughly in the order I'd take
the open ones on.

## Open

- Route the quarterly new-data alert somewhere other than GitHub. The detection
  job currently opens a repo issue when a new FDIC quarter lands; wiring it to
  Slack or email as well would make it useful away from the repo.
- Make the charts themselves readable by screen readers. The canvas charts
  aren't, and only the analytical pages currently back them with data tables. A
  per-chart data-table toggle would close that gap on the profile pages too.

## Assessed and rejected

- Deep-linkable per-bank profile pages. I built this with Evidence templated
  pages, one route per bank, and the build works, but it prerenders a query
  result per page per chart, roughly 15,000 files, and the GitHub Pages deploy
  can't sync that many. It fails at the `syncing_files` step every time. The
  single searchable profile page is about 270 files and deploys cleanly, so
  that's what ships. Real deep-links would need a host that handles the file
  count (Cloudflare Pages, Netlify) or Evidence dropping per-page query
  prerendering. The full story is in `docs/decisions.md`.
- Folding the metric display-name maps into a dbt seed. On inspection the only
  real duplication is a four-row business-model map shared by two pages. A seed
  plus its export plus per-page joins would add more plumbing than it removes,
  so the inline maps stay on purpose.

## Shipped from this list

Workflow improvements:

- The outlier screen shows the biggest quarter-over-quarter composite moves in
  a band, not just the current level.
- The peer explorer can highlight a chosen bank on the distribution.

Analysis improvements:

- The profile page charts a bank's composite over time, tying it back to the
  screen.
- The outlier screen shows how correlated the six screen metrics are; the
  composite stays unweighted regardless.

Operational improvements:

- The weekly job checks FRED feed freshness and flags a stale feed instead of
  silently deploying old H.8 numbers.
- A new FDIC quarter opens a repo issue announcing it, rather than redeploying
  in silence.
- Accessibility pass: the dark theme already clears WCAG AA (about 12:1 text
  contrast, clean heading order, focusable controls), and the architecture
  image got real alt text.

Earlier polish:

- Human-readable metric and business-model labels everywhere.
- Median, 10th, and 90th percentile reference lines on the peer-explorer
  histogram.
- A data-vintage line on the landing page.
- Architecture diagram corrections: model count fixed at twelve, and the CI
  bullet now says pull requests build against a committed sample rather than
  the warehouse.
