-- One row per GA4 event from Google's obfuscated ecommerce sample. All
-- flattening lives in the shared macro so the own-property staging model
-- (stg_ga4__events) is guaranteed the same shape. Suffix bounds are the
-- dataset's full published window.

{{ ga4_events_normalized(source('ga4_sample', 'events'),
                         suffix_start='20201101', suffix_end='20210131') }}
