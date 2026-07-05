{#
  GA4 export events share one schema across properties, so the sample-dataset
  models and the (future) own-property models flatten through these macros.
  event_params is ARRAY<STRUCT<key, value STRUCT<string_value, int_value,
  float_value, double_value>>>; a param's slot is not guaranteed — GA4 writes
  session_engaged as a string on some events, so int extraction must fall back
  to string_value.
#}

{% macro ga4_param_str(key) %}
    (select p.value.string_value from unnest(event_params) as p where p.key = '{{ key }}')
{% endmacro %}

{% macro ga4_param_int(key) %}
    (select coalesce(p.value.int_value, safe_cast(p.value.string_value as int64))
     from unnest(event_params) as p where p.key = '{{ key }}')
{% endmacro %}

{% macro ga4_events_normalized(relation, suffix_start=none, suffix_end=none) %}
select
    parse_date('%Y%m%d', event_date)                     as event_date,
    timestamp_micros(event_timestamp)                    as event_ts,
    event_name,
    user_pseudo_id,
    {{ ga4_param_int('ga_session_id') }}                 as ga_session_id,
    {{ ga4_param_int('ga_session_number') }}             as ga_session_number,
    concat(user_pseudo_id, '-',
           cast({{ ga4_param_int('ga_session_id') }} as string)) as session_key,
    {{ ga4_param_str('page_location') }}                 as page_location,
    {{ ga4_param_str('page_title') }}                    as page_title,
    {{ ga4_param_str('page_referrer') }}                 as page_referrer,
    {{ ga4_param_int('session_engaged') }}               as session_engaged,
    {{ ga4_param_int('engagement_time_msec') }}          as engagement_time_msec,
    device.category                                      as device_category,
    device.operating_system                              as operating_system,
    device.web_info.browser                              as browser,
    geo.country                                          as country,
    geo.region                                           as region,
    geo.city                                             as city,
    platform,
    -- traffic_source is USER-scoped first-touch acquisition, not the session's
    -- own channel; the session-scoped signal lives in event params and is often
    -- null. Both are kept, named for what they are.
    traffic_source.source                                as first_touch_source,
    traffic_source.medium                                as first_touch_medium,
    traffic_source.name                                  as first_touch_name,
    {{ ga4_param_str('source') }}                        as event_source,
    {{ ga4_param_str('medium') }}                        as event_medium,
    {{ ga4_param_str('campaign') }}                      as event_campaign,
    ecommerce.purchase_revenue_in_usd                    as purchase_revenue_usd,
    ecommerce.transaction_id                             as transaction_id,
    timestamp_micros(user_first_touch_timestamp)         as user_first_touch_ts
from {{ relation }}
{% if suffix_start is not none and suffix_end is not none %}
-- shard pruning: GA4 exports are one table per day; without suffix bounds
-- BigQuery scans every shard
where _table_suffix between '{{ suffix_start }}' and '{{ suffix_end }}'
{% endif %}
{% endmacro %}
