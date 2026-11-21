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
    SELECT s1.person_id, s1.index_date
    FROM step1_osa s1
    JOIN public.observation_period op ON s1.person_id = op.person_id
    WHERE op.observation_period_start_date <= (s1.index_date - INTERVAL '365 days')
      AND op.observation_period_end_date >= s1.index_date
),
step3_adult AS (
    SELECT s2.person_id, s2.index_date
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
    SELECT s3.person_id, s3.index_date
    FROM step3_adult s3
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.device_exposure de
        JOIN pap_concepts pc ON de.device_concept_id = pc.concept_id
        WHERE de.person_id = s3.person_id
          AND de.device_exposure_start_date < s3.index_date
    )
),
attrition_counts AS (
    SELECT 0 AS step_order, '0. Base Sleep Apnea cohort' AS criterion, COUNT(*) AS n_patients FROM step0_base
    UNION ALL
    SELECT 1 AS step_order, '1. Restricted to Obstructive Sleep Apnea (OSA)' AS criterion, COUNT(*) AS n_patients FROM step1_osa
    UNION ALL
    SELECT 2 AS step_order, '2. >= 365 days pre-index continuous observation' AS criterion, COUNT(*) AS n_patients FROM step2_obs
    UNION ALL
    SELECT 3 AS step_order, '3. Adult population (18+ y/o at index)' AS criterion, COUNT(*) AS n_patients FROM step3_adult
    UNION ALL
    SELECT 4 AS step_order, '4. No CPAP therapy prior to index' AS criterion, COUNT(*) AS n_patients FROM step4_naive
)
SELECT
    criterion,
    n_patients,
    LAG(n_patients) OVER (ORDER BY step_order) - n_patients AS n_excluded,
    ROUND(100.0 * n_patients / FIRST_VALUE(n_patients) OVER (ORDER BY step_order), 1) AS pct_of_base
FROM attrition_counts
ORDER BY step_order;