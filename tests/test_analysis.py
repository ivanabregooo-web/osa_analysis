import numpy as np
import pandas as pd
import pytest

from osa_epi.analysis import (
    aggregate_patient_bmi,
    compute_kaplan_meier,
    compute_logrank_test,
    format_comorbidities,
    prepare_demographics,
    summarize_continuous,
    summarize_cpap_persistence,
    survival_at_times,
)


def test_prepare_demographics_computes_age_and_followup() -> None:
    raw = pd.DataFrame(
        {
            "person_id": [1, 2],
            "cohort_start_date": ["2020-05-10", "2021-01-15"],
            "cohort_end_date": ["2021-05-10", "2021-02-14"],
            "year_of_birth": [1970, 1985],
            "sex": ["Male", "female"],
        }
    )
    res = prepare_demographics(raw)

    assert res["age_at_index"].tolist() == [50, 36]
    assert res["followup_days"].tolist() == [365, 30]
    assert res["sex"].tolist() == ["MALE", "FEMALE"]


def test_prepare_demographics_raises_on_missing_column() -> None:
    incomplete = pd.DataFrame({"person_id": [1]})
    with pytest.raises(ValueError, match="Missing required columns"):
        prepare_demographics(incomplete)


def test_summarize_continuous_returns_expected_quartiles() -> None:
    s = pd.Series([20.0, 30.0, 40.0, 50.0, 60.0])
    stats = summarize_continuous(s)
    assert stats == {"median": 40.0, "q25": 30.0, "q75": 50.0}


def test_summarize_continuous_handles_all_nan() -> None:
    s = pd.Series([np.nan, np.nan])
    stats = summarize_continuous(s)
    assert np.isnan(stats["median"])
    assert np.isnan(stats["q25"])
    assert np.isnan(stats["q75"])


def test_format_comorbidities_sorts_and_formats_labels() -> None:
    raw = pd.DataFrame(
        {
            "concept_name": ["Hypertension", "Obesity", "Type 2 diabetes"],
            "patient_count": [120, 180, 90],
            "prevalence_pct": [33.5, 50.3, 25.1],
        }
    )
    res = format_comorbidities(raw, top_n=2)

    assert len(res) == 2
    assert res["concept_name"].tolist() == ["Obesity", "Hypertension"]
    assert res["bar_label"].tolist() == ["180 (50.3%)", "120 (33.5%)"]


def test_aggregate_patient_bmi_averages_by_patient() -> None:
    raw = pd.DataFrame(
        {
            "person_id": [10, 10, 20],
            "sex": ["Male", "Male", "female"],
            "bmi": [28.0, 32.0, 24.5],
        }
    )
    res = aggregate_patient_bmi(raw)

    assert res["person_id"].tolist() == [10, 20]
    assert res["mean_bmi"].tolist() == [30.0, 24.5]
    assert res["n_measurements"].tolist() == [2, 1]
    assert res["sex"].tolist() == ["MALE", "FEMALE"]


def test_compute_kaplan_meier_and_landmarks() -> None:
    # 4 subjects: event at t=10, censored at t=20, event at t=30, censored at t=40
    # At t=10: 3/4 = 0.75; at t=30: 0.75 * (1/2) = 0.375
    km = compute_kaplan_meier([10, 20, 30, 40], [1, 0, 1, 0])

    assert km["time"].tolist() == [0.0, 10.0, 30.0, 40.0]
    assert km["survival"].tolist() == pytest.approx([1.0, 0.75, 0.375, 0.375])
    assert (km["ci_lower"] <= km["survival"]).all()
    assert (km["ci_upper"] >= km["survival"]).all()

    landmarks = survival_at_times(km, time_points=(5.0, 15.0, 35.0, 100.0))
    assert landmarks[5.0] == pytest.approx(1.0)
    assert landmarks[15.0] == pytest.approx(0.75)
    assert landmarks[35.0] == pytest.approx(0.375)
    assert np.isnan(landmarks[100.0])


def test_compute_logrank_test_detects_difference() -> None:
    df = pd.DataFrame(
        {
            "time": [10, 12, 15, 20, 200, 250, 300, 400],
            "event": [1, 1, 1, 1, 0, 0, 0, 0],
            "sex": [
                "MALE",
                "MALE",
                "MALE",
                "MALE",
                "FEMALE",
                "FEMALE",
                "FEMALE",
                "FEMALE",
            ],
        }
    )
    res = compute_logrank_test(
        df, duration_col="time", event_col="event", group_col="sex"
    )
    assert res["df"] == 1
    assert res["chi2"] > 3.84
    assert res["p_value"] < 0.05


def test_summarize_cpap_persistence_returns_overall_and_sex_rows() -> None:
    df = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "sex": ["Male", "Male", "Female", "Female"],
            "initiated_pap": [1, 0, 1, 1],
            "pap_discontinued_event": [1, np.nan, 0, 1],
            "pap_persistence_days": [120.0, np.nan, 400.0, 60.0],
            "days_to_pap_initiation": [14.0, np.nan, 7.0, 30.0],
        }
    )
    summary = summarize_cpap_persistence(df)

    assert summary["stratum"].tolist() == ["OVERALL", "FEMALE", "MALE"]
    overall = summary.iloc[0]
    assert overall["cohort_n"] == 4
    assert overall["cpap_initiators_n"] == 3
    assert overall["cpap_initiation_pct"] == 75.0
    assert overall["discontinued_n"] == 2
