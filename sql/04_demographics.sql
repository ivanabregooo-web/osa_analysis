SELECT
    c.subject_id AS person_id,
    c.cohort_start_date,
    c.cohort_end_date,
    p.year_of_birth,
    COALESCE(gc.concept_name, p.gender_source_value, 'Unknown') AS sex
FROM results.cohort c
JOIN public.person p
    ON c.subject_id = p.person_id
LEFT JOIN public.concept gc
    ON p.gender_concept_id = gc.concept_id
WHERE c.cohort_definition_id = :cohort_definition_id
ORDER BY c.subject_id;