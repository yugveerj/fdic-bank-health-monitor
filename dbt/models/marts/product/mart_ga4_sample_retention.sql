-- Weekly retention triangle. cohort_week is each user's first session week
-- inside the sample window — the dataset has no history before it, so early
-- cohorts absorb some returning users who look new. week_number is capped at
-- 12 (the window itself only spans ~13 weeks). Week 0 is included and is 1.0
-- by construction; the data test asserts it stays that way.

with sessions as (
    select
        user_pseudo_id,
        date_trunc(session_date, week(monday)) as activity_week
    from {{ ref('int_ga4_sample_sessions') }}
),

cohorts as (
    select user_pseudo_id, min(activity_week) as cohort_week
    from sessions
    group by user_pseudo_id
),

cohort_sizes as (
    select cohort_week, count(*) as cohort_size
    from cohorts
    group by cohort_week
),

activity as (
    select distinct
        c.cohort_week,
        s.user_pseudo_id,
        -- both dates are Monday-aligned, so day-diff/7 is an exact week count
        div(date_diff(s.activity_week, c.cohort_week, day), 7) as week_number
    from sessions s
    join cohorts c using (user_pseudo_id)
)

select
    a.cohort_week,
    a.week_number,
    cs.cohort_size,
    count(distinct a.user_pseudo_id)                        as active_users,
    safe_divide(count(distinct a.user_pseudo_id), cs.cohort_size) as retention_pct
from activity a
join cohort_sizes cs using (cohort_week)
where a.week_number <= 12
group by a.cohort_week, a.week_number, cs.cohort_size
