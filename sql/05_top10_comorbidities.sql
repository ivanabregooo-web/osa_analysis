WITH sleep_apnea_root AS (
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
    SELECT concept_id FROM sleep_apnea_root
    UNION
    SELECT ca.descendant_concept_id AS concept_id
    FROM public.concept_ancestor ca
    JOIN sleep_apnea_root r ON ca.ancestor_concept_id = r.concept_id
),
cohort_total AS (
    SELECT COUNT(DISTINCT subject_id) AS total_patients
    FROM results.cohort
    WHERE cohort_definition_id = :cohort_definition_id
)
SELECT
    c.concept_id,
    c.concept_name,
    COUNT(DISTINCT coh.subject_id) AS patient_count,
    ROUND(
        100.0 * COUNT(DISTINCT coh.subject_id) / NULLIF(MAX(ct.total_patients), 0),
        1
    ) AS prevalence_pct
FROM results.cohort coh
CROSS JOIN cohort_total ct
JOIN public.condition_occurrence co
    ON coh.subject_id = co.person_id
JOIN public.concept c
    ON co.condition_concept_id = c.concept_id
WHERE coh.cohort_definition_id = :cohort_definition_id
  AND co.condition_start_date <= coh.cohort_start_date
  AND c.domain_id = 'Condition'
  AND c.standard_concept = 'S'
  AND c.invalid_reason IS NULL
  AND c.concept_id NOT IN (SELECT concept_id FROM sleep_apnea_concepts)
GROUP BY c.concept_id, c.concept_name
ORDER BY patient_count DESC, c.concept_name ASC
LIMIT 10;