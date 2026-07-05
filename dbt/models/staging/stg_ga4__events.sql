-- One row per GA4 event from the project's own property, same shape as
-- stg_ga4_sample__events. Disabled until Phase E creates the property and the
-- daily export lands; flipping ga4_export_enabled (and setting
-- GA4_EXPORT_DATASET) turns it on with no other changes.

{{ config(enabled=var('ga4_export_enabled', false)) }}

{{ ga4_events_normalized(source('ga4_export', 'events')) }}
