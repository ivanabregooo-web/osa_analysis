WITH cohort_obs AS (
    SELECT
        c.subject_id AS person_id,
        CAST(c.cohort_start_date AS DATE) AS cohort_start_date,
        CAST(MIN(op.observation_period_end_date) AS DATE) AS op_end_date
    FROM results.cohort c
    JOIN public.observation_period op
        ON c.subject_id = op.person_id
       AND op.observation_period_start_date <= c.cohort_start_date
       AND op.observation_period_end_date >= c.cohort_start_date
    WHERE c.cohort_definition_id = :cohort_definition_id
    GROUP BY c.subject_id, c.cohort_start_date
),
pap_concepts AS (
    SELECT 45765273 AS concept_id
    UNION
    SELECT ca.descendant_concept_id AS concept_id
    FROM public.concept_ancestor ca
    WHERE ca.ancestor_concept_id = 45765273
),
pap_events AS (
    SELECT
        co.person_id,
        CAST(de.device_exposure_start_date AS DATE) AS event_start,
        GREATEST(
            CAST(de.device_exposure_start_date AS DATE),
            CAST(COALESCE(de.device_exposure_end_date, co.op_end_date) AS DATE)
        ) AS event_end
    FROM cohort_obs co
    JOIN public.device_exposure de
        ON co.person_id = de.person_id
    JOIN pap_concepts pc
        ON de.device_concept_id = pc.concept_id
    WHERE de.device_exposure_start_date >= co.cohort_start_date
),
pap_lagged AS (
    SELECT
        person_id,
        event_start,
        event_end,
        MAX(event_end) OVER (
            PARTITION BY person_id
            ORDER BY event_start, event_end
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS prev_max_end
    FROM pap_events
),
pap_island_flags AS (
    SELECT
        person_id,
        event_start,
        event_end,
        CASE
            WHEN prev_max_end IS NULL
              OR event_start >= CAST(prev_max_end + INTERVAL '30 days' AS DATE)
            THEN 1
            ELSE 0
        END AS is_new_island
    FROM pap_lagged
),
pap_islands AS (
    SELECT
        person_id,
        SUM(is_new_island) OVER (
            PARTITION BY person_id
            ORDER BY event_start, event_end
            ROWS UNBOUNDED PRECEDING
        ) AS island_id,
        event_start,
        event_end
    FROM pap_island_flags
),
first_pap_episode AS (
    SELECT
        person_id,
        MIN(event_start) AS first_pap_start,
        MAX(event_end) AS first_pap_end,
        CAST(MAX(event_end) + INTERVAL '30 days' AS DATE) AS pap_exit_date
    FROM pap_islands
    WHERE island_id = 1
    GROUP BY person_id
)
SELECT
    co.person_id,
    COALESCE(gc.concept_name, p.gender_source_value, 'Unknown') AS sex,
    co.cohort_start_date,
    co.op_end_date,
    CAST(d.death_date AS DATE) AS death_date,
    LEAST(co.op_end_date, CAST(d.death_date AS DATE)) AS survival_end_date,
    CASE
        WHEN d.death_date IS NOT NULL
         AND CAST(d.death_date AS DATE) <= co.op_end_date
        THEN 1
        ELSE 0
    END AS death_event,
    GREATEST(
        0,
        CAST(LEAST(co.op_end_date, CAST(d.death_date AS DATE)) - co.cohort_start_date AS INTEGER)
    ) AS survival_days,
    CASE WHEN fp.first_pap_start IS NOT NULL THEN 1 ELSE 0 END AS initiated_pap,
    fp.first_pap_start,
    fp.first_pap_end,
    fp.pap_exit_date,
    CASE
        WHEN fp.first_pap_start IS NULL THEN NULL
        ELSE LEAST(co.op_end_date, CAST(d.death_date AS DATE), fp.pap_exit_date)
    END AS pap_persistence_end_date,
    CASE
        WHEN fp.first_pap_start IS NULL THEN NULL
        WHEN fp.pap_exit_date <= LEAST(co.op_end_date, CAST(d.death_date AS DATE)) THEN 1
        ELSE 0
    END AS pap_discontinued_event,
    CASE
        WHEN fp.first_pap_start IS NULL THEN NULL
        ELSE GREATEST(
            0,
            CAST(
                LEAST(co.op_end_date, CAST(d.death_date AS DATE), fp.pap_exit_date)
                - fp.first_pap_start AS INTEGER
            )
        )
    END AS pap_persistence_days,
    CASE
        WHEN fp.first_pap_start IS NULL THEN NULL
        ELSE GREATEST(0, CAST(fp.first_pap_start - co.cohort_start_date AS INTEGER))
    END AS days_to_pap_initiation
FROM cohort_obs co
JOIN public.person p
    ON co.person_id = p.person_id
LEFT JOIN public.concept gc
    ON p.gender_concept_id = gc.concept_id
LEFT JOIN public.death d
    ON co.person_id = d.person_id
LEFT JOIN first_pap_episode fp
    ON co.person_id = fp.person_id
ORDER BY co.person_id;