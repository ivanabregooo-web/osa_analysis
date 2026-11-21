WITH bmi_concepts AS (
    SELECT concept_id
    FROM public.concept
    WHERE domain_id = 'Measurement'
      AND standard_concept = 'S'
      AND invalid_reason IS NULL
      AND (
          (vocabulary_id = 'LOINC' AND concept_code = '39156-5')
          OR concept_id IN (3038553, 4245997)
      )
)
SELECT
    coh.subject_id AS person_id,
    COALESCE(gc.concept_name, p.gender_source_value, 'Unknown') AS sex,
    m.measurement_date,
    m.value_as_number AS bmi
FROM results.cohort coh
JOIN public.person p
    ON coh.subject_id = p.person_id
LEFT JOIN public.concept gc
    ON p.gender_concept_id = gc.concept_id
JOIN public.measurement m
    ON coh.subject_id = m.person_id
JOIN bmi_concepts bc
    ON m.measurement_concept_id = bc.concept_id
WHERE coh.cohort_definition_id = :cohort_definition_id
  AND m.measurement_date <= coh.cohort_start_date
  AND m.value_as_number IS NOT NULL
  AND m.value_as_number BETWEEN 10 AND 100
ORDER BY coh.subject_id, m.measurement_date;