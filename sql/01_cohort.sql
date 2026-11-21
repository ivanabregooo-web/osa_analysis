DELETE FROM results.cohort
WHERE cohort_definition_id = :cohort_definition_id;

INSERT INTO results.cohort (
    cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
)
WITH root_concept AS (
    SELECT concept_id
    FROM public.concept
    WHERE LOWER(concept_name) = 'sleep apnea'
      AND vocabulary_id = 'SNOMED'
      AND standard_concept = 'S'
      AND domain_id = 'Condition'
      AND invalid_reason IS NULL
    ORDER BY concept_id
    LIMIT 1
),
sleep_apnea_concepts AS (
    SELECT concept_id FROM root_concept
    UNION
    SELECT ca.descendant_concept_id AS concept_id
    FROM public.concept_ancestor ca
    JOIN root_concept rc ON ca.ancestor_concept_id = rc.concept_id
    JOIN public.concept c ON ca.descendant_concept_id = c.concept_id
    WHERE c.invalid_reason IS NULL
),
osa_root AS (
    SELECT concept_id
    FROM public.concept
    WHERE LOWER(concept_name) = 'obstructive sleep apnea syndrome'
      AND vocabulary_id = 'SNOMED'
      AND standard_concept = 'S'
      AND domain_id = 'Condition'
      AND invalid_reason IS NULL
    ORDER BY concept_id
    LIMIT 1
),
osa_concepts AS (
    SELECT concept_id FROM osa_root
    UNION
    SELECT ca.descendant_concept_id AS concept_id
    FROM public.concept_ancestor ca
    JOIN osa_root r ON ca.ancestor_concept_id = r.concept_id
    JOIN public.concept c ON ca.descendant_concept_id = c.concept_id
    WHERE c.invalid_reason IS NULL
),
step0_base AS (
    SELECT
        co.person_id,
        MIN(co.condition_start_date) AS index_date
    FROM public.condition_occurrence co
    JOIN sleep_apnea_concepts sac ON co.condition_concept_id = sac.concept_id
    GROUP BY co.person_id
),
step1_osa AS (
    SELECT DISTINCT b.person_id, b.index_date
    FROM step0_base b
    JOIN public.condition_occurrence co
        ON b.person_id = co.person_id
       AND co.condition_start_date = b.index_date
    JOIN osa_concepts oc
        ON co.condition_concept_id = oc.concept_id
),
step2_obs AS (
    SELECT
        s1.person_id,
        s1.index_date,
        MIN(op.observation_period_end_date) AS op_end_date
    FROM step1_osa s1
    JOIN public.observation_period op ON s1.person_id = op.person_id
    WHERE op.observation_period_start_date <= (s1.index_date - INTERVAL '365 days')
      AND op.observation_period_end_date >= s1.index_date
    GROUP BY s1.person_id, s1.index_date
),
step3_adult AS (
    SELECT
        s2.person_id,
        s2.index_date,
        s2.op_end_date
    FROM step2_obs s2
    JOIN public.person p ON s2.person_id = p.person_id
    WHERE (EXTRACT(YEAR FROM s2.index_date) - p.year_of_birth) >= 18
),
pap_concepts AS (
    SELECT 45765273 AS concept_id
    UNION
    SELECT ca.descendant_concept_id AS concept_id
    FROM public.concept_ancestor ca
    WHERE ca.ancestor_concept_id = 45765273
),
step4_naive AS (
    SELECT
        s3.person_id,
        s3.index_date,
        s3.op_end_date
    FROM step3_adult s3
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.device_exposure de
        JOIN pap_concepts pc ON de.device_concept_id = pc.concept_id
        WHERE de.person_id = s3.person_id
          AND de.device_exposure_start_date < s3.index_date
    )
),
pap_events AS (
    SELECT
        s4.person_id,
        CAST(de.device_exposure_start_date AS DATE) AS event_start,
        GREATEST(
            CAST(de.device_exposure_start_date AS DATE),
            CAST(COALESCE(de.device_exposure_end_date, s4.op_end_date) AS DATE)
        ) AS event_end
    FROM step4_naive s4
    JOIN public.device_exposure de ON s4.person_id = de.person_id
    JOIN pap_concepts pc ON de.device_concept_id = pc.concept_id
    WHERE de.device_exposure_start_date >= s4.index_date
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
        CAST(MAX(event_end) + INTERVAL '30 days' AS DATE) AS pap_exit_date
    FROM pap_islands
    WHERE island_id = 1
    GROUP BY person_id
),
cohort_exit AS (
    SELECT
        s4.person_id AS subject_id,
        s4.index_date AS cohort_start_date,
        GREATEST(
            s4.index_date,
            LEAST(
                CAST(s4.op_end_date AS DATE),
                CAST(d.death_date AS DATE),
                fp.pap_exit_date
            )
        ) AS cohort_end_date
    FROM step4_naive s4
    LEFT JOIN public.death d ON s4.person_id = d.person_id
    LEFT JOIN first_pap_episode fp ON s4.person_id = fp.person_id
)
SELECT
    :cohort_definition_id AS cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
FROM cohort_exit
ORDER BY subject_id;