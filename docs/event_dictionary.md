# GA4 event dictionary

The instrumentation-design artifact for the monitor's analytics. Every event the
GA4 work touches — auto-collected, custom, or borrowed from Google's public
sample — gets a row here before any code references it. A row is added when a
new event is designed, not after it ships; the `status` column tracks the gap.
Later projects that add events (Phase E gtag work, anything in the backlog)
update this file in the same commit.

Standing rule: no event carries PII. No names, no email addresses, no free-text
input. The only identifier any event carries is an FDIC certificate number,
which is public data about an institution, not a person.

## Auto-collected events we rely on

GA4 sends these with no code on our side beyond the base gtag snippet
(enhanced measurement on). Listed because the Stage-1 marts and the eventual
monitor-property marts query them by name.

| Event | What it tells us | Source |
|---|---|---|
| `page_view` | Which of the five dashboard pages get read | automatic |
| `session_start` | Session boundaries for engagement marts | automatic |
| `first_visit` | New-visitor share | automatic |
| `user_engagement` | Engaged time per page | automatic |
| `scroll` | Whether long pages (index, backtest) get read past the fold | automatic |

## Custom events — monitor property

Status is `planned` until Phase E ships the GA4 property and the gtag calls
land in the Evidence layout. Triggers name the actual UI as it exists on the
deployed pages today.

| Event | Trigger | Properties | Destination property | Status |
|---|---|---|---|---|
| `bank_selected` | Bank chosen in the "Institution (closed banks included)" dropdown on the bank profile page | `bank` STRING — the option's display label ("Name — City, ST"); the cert never reaches the DOM the listener sees, and the label is public institution data | FDIC Bank Health Monitor (G-44RCFYRK9W) | live |
| `metric_selected` | Metric chosen in the "Metric" dropdown on the peer-group explorer | `metric` STRING | FDIC Bank Health Monitor (G-44RCFYRK9W) | live |
| `excel_download` | Click on any `latest.xlsx` link (versionless, so there is no version to record) | none | FDIC Bank Health Monitor (G-44RCFYRK9W) | live |
| `tableau_click` | Outbound click on any `public.tableau.com` link | none | FDIC Bank Health Monitor (G-44RCFYRK9W) | live |
| `looker_click` | Outbound click on any `datastudio.google.com` / `lookerstudio.google.com` link | none | FDIC Bank Health Monitor (G-44RCFYRK9W) | live |

## Public-sample events — Stage-1 marts

Google sample, read-only — not ours. The Stage-1 staging/marts run against
`bigquery-public-data.ga4_obfuscated_sample_ecommerce` (the Google Merchandise
Store), so the funnel events are ecommerce events we did not design and cannot
change. They are listed so the mart SQL has a documented contract; none of them
will ever fire on the monitor property.

| Event | Used for |
|---|---|
| `view_item` | Funnel stage 1 (view) |
| `add_to_cart` | Funnel stage 2 (cart) |
| `begin_checkout` | Evidence of cart passage in the closed funnel; `checkouts` count on the session model |
| `purchase` | Funnel stage 3 / conversion; purchase counts and revenue everywhere |
| `session_start` | Kept in staging; sessions themselves derive from the `ga_session_id` param on every event |
| `first_visit` | New-vs-returning split (`new_users` on the daily mart) |
| `page_view` | Pageview counts on the session and daily marts |
