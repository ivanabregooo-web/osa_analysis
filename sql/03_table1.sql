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
),
baseline_bmi AS (
    SELECT DISTINCT ON (c.subject_id)
        c.subject_id,
        m.value_as_number AS bmi
    FROM results.cohort c
    JOIN public.measurement m
        ON c.subject_id = m.person_id
    JOIN bmi_concepts bc
        ON m.measurement_concept_id = bc.concept_id
    WHERE c.cohort_definition_id = :cohort_definition_id
      AND m.measurement_date BETWEEN (c.cohort_start_date - INTERVAL '365 days') AND c.cohort_start_date
      AND m.value_as_number IS NOT NULL
      AND m.value_as_number BETWEEN 10 AND 100
    ORDER BY c.subject_id, m.measurement_date DESC, m.measurement_id DESC
),
cohort_demographics AS (
    SELECT
        c.subject_id,
        COALESCE(gc.concept_name, p.gender_source_value, 'Unknown') AS sex,
        CAST(EXTRACT(YEAR FROM c.cohort_start_date) - p.year_of_birth AS NUMERIC) AS age_at_index,
        bb.bmi,
        CAST(CAST(c.cohort_end_date AS DATE) - CAST(c.cohort_start_date AS DATE) AS NUMERIC) AS followup_days
    FROM results.cohort c
    JOIN public.person p
        ON c.subject_id = p.person_id
    LEFT JOIN public.concept gc
        ON p.gender_concept_id = gc.concept_id
    LEFT JOIN baseline_bmi bb
        ON c.subject_id = bb.subject_id
    WHERE c.cohort_definition_id = :cohort_definition_id
),
summary_stats AS (
    SELECT
        COUNT(*) AS total_patients,
        COUNT(bmi) AS n_with_bmi,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY age_at_index) AS age_median,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY age_at_index) AS age_q25,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY age_at_index) AS age_q75,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY bmi) AS bmi_median,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bmi) AS bmi_q25,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bmi) AS bmi_q75,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY followup_days) AS fu_median,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY followup_days) AS fu_q25,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY followup_days) AS fu_q75
    FROM cohort_demographics
),
sex_counts AS (
    SELECT
        sex,
        COUNT(*) AS n_sex,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_sex
    FROM cohort_demographics
    GROUP BY sex
)
SELECT
    characteristic,
    value
FROM (
    SELECT
        1 AS row_order,
        'Total patients (N)' AS characteristic,
        CAST(total_patients AS TEXT) AS value
    FROM summary_stats

    UNION ALL

    SELECT
        2 AS row_order,
        'Sex: ' || sex AS characteristic,
        CAST(n_sex AS TEXT) || ' (' || CAST(pct_sex AS TEXT) || '%)' AS value
    FROM sex_counts

    UNION ALL

    SELECT
        3 AS row_order,
        'Age at index (years)' AS characteristic,
        CAST(ROUND(CAST(age_median AS NUMERIC), 1) AS TEXT)
            || ' (' || CAST(ROUND(CAST(age_q25 AS NUMERIC), 1) AS TEXT)
            || ' - ' || CAST(ROUND(CAST(age_q75 AS NUMERIC), 1) AS TEXT) || ')' AS value
    FROM summary_stats

    UNION ALL

    SELECT
        4 AS row_order,
        'Baseline bmi (kg/m2)' AS characteristic,
        COALESCE(
            CAST(ROUND(CAST(bmi_median AS NUMERIC), 1) AS TEXT)
                || ' (' || CAST(ROUND(CAST(bmi_q25 AS NUMERIC), 1) AS TEXT)
                || ' - ' || CAST(ROUND(CAST(bmi_q75 AS NUMERIC), 1) AS TEXT) || ')',
            'N/A'
        ) AS value
    FROM summary_stats

    UNION ALL

    SELECT
        5 AS row_order,
        'Baseline bmi recorded' AS characteristic,
        CAST(n_with_bmi AS TEXT) || ' ('
            || CAST(ROUND(100.0 * n_with_bmi / NULLIF(total_patients, 0), 1) AS TEXT)
            || '%)' AS value
    FROM summary_stats

    UNION ALL

    SELECT
        6 AS row_order,
        'Follow-up duration (days)' AS characteristic,
        CAST(ROUND(CAST(fu_median AS NUMERIC), 1) AS TEXT)
            || ' (' || CAST(ROUND(CAST(fu_q25 AS NUMERIC), 1) AS TEXT)
            || ' - ' || CAST(ROUND(CAST(fu_q75 AS NUMERIC), 1) AS TEXT) || ')' AS value
    FROM summary_stats
) table_1
ORDER BY row_order, characteristic;