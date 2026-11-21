from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from osa_epi.visualization import (
    plot_age_distribution_by_sex,
    plot_bmi_distribution,
    plot_kaplan_meier_by_sex,
    plot_top_comorbidities,
)


def test_plot_age_distribution_creates_one_subplot_per_sex(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "sex": ["MALE", "MALE", "FEMALE", "FEMALE"],
            "age_at_index": [45, 55, 38, 62],
        }
    )
    out_file = tmp_path / "age_by_sex.png"
    fig, axes = plot_age_distribution_by_sex(df, output_path=out_file)

    assert len(axes) == 2
    assert axes[0].get_title() == "Female (n = 2)"
    assert axes[1].get_title() == "Male (n = 2)"
    assert out_file.exists()
    plt.close(fig)


def test_plot_top_comorbidities_saves_bar_chart(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "concept_name": ["Obesity", "Essential hypertension"],
            "patient_count": [180, 140],
            "prevalence_pct": [50.3, 39.1],
            "bar_label": ["180 (50.3%)", "140 (39.1%)"],
        }
    )
    out_file = tmp_path / "top_comorbidities.png"
    fig, ax = plot_top_comorbidities(df, output_path=out_file)

    assert len(ax.patches) == 2
    assert out_file.exists()
    plt.close(fig)

    def test_plot_bmi_distribution_hued_by_sex(tmp_path: Path) -> None:
        df = pd.DataFrame(
            {
                "person_id": [1, 2, 3, 4],
                "sex": ["MALE", "MALE", "FEMALE", "FEMALE"],
                "mean_bmi": [24.2, 27.8, 31.5, 35.0],
            }
        )
        out_file = tmp_path / "bmi_dist_by_sex.png"
        fig, ax = plot_bmi_distribution(df, output_path=out_file)

        legend_texts = [t.get_text() for t in ax.get_legend().get_texts()]
        assert any(t.startswith("Female (n=2)") for t in legend_texts)
        assert any(t.startswith("Male (n=2)") for t in legend_texts)
        assert out_file.exists()
        plt.close(fig)


def test_plot_kaplan_meier_by_sex_saves_step_plot(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "sex": ["MALE", "MALE", "MALE", "FEMALE", "FEMALE", "FEMALE"],
            "duration": [30, 90, 180, 60, 200, 365],
            "event": [1, 0, 1, 1, 0, 0],
        }
    )
    out_file = tmp_path / "km_curve.png"
    fig, ax = plot_kaplan_meier_by_sex(
        df,
        duration_col="duration",
        event_col="event",
        title="Test KM curve",
        xlabel="Days",
        ylabel="Survival probability",
        output_path=out_file,
    )

    assert len(ax.lines) == 2
    assert out_file.exists()
    plt.close(fig)
