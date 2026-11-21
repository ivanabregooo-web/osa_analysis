from pathlib import Path

import matplotlib.pyplot as plt
from sqlalchemy.engine import Engine

from osa_epi.analysis import (
    aggregate_patient_bmi,
    format_comorbidities,
    prepare_demographics,
    summarize_cpap_persistence,
)
from osa_epi.config import DEFAULT_COHORT_ID, FIGURES_DIR, TABLES_DIR
from osa_epi.db import execute_sql_script, get_engine, run_sql_query
from osa_epi.visualization import (
    plot_age_distribution_by_sex,
    plot_bmi_distribution,
    plot_kaplan_meier_by_sex,
    plot_top_comorbidities,
)


def run_pipeline(
    engine: Engine,
    cohort_definition_id: int = DEFAULT_COHORT_ID,
    tables_dir: Path = TABLES_DIR,
    figures_dir: Path = FIGURES_DIR,
) -> None:
    """Execute the end-to-end OSA cohort extraction, summary tables, and plots."""
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    params = {"cohort_definition_id": cohort_definition_id}

    print(f"[1/8] Extracting OSA cohort (id={cohort_definition_id})...")
    execute_sql_script(engine, "01_cohort.sql", params=params)

    print("[2/8] Creating attrition table...")
    attrition_df = run_sql_query(engine, "02_attrition.sql")
    attrition_path = tables_dir / "attrition_table.csv"
    attrition_df.to_csv(attrition_path, index=False)

    print("[3/8] Creating Table 1 baseline characteristics...")
    table1_df = run_sql_query(engine, "03_table1.sql", params=params)
    table1_path = tables_dir / "table1_baseline.csv"
    table1_df.to_csv(table1_path, index=False)

    print("[4/8] Plotting age distribution by sex...")
    raw_demo_df = run_sql_query(engine, "04_demographics.sql", params=params)
    demo_df = prepare_demographics(raw_demo_df)
    age_fig, _ = plot_age_distribution_by_sex(
        demo_df,
        output_path=figures_dir / "age_distribution_by_sex.png",
    )
    plt.close(age_fig)

    print("[5/8] Extracting top-10 baseline comorbidities...")
    raw_comorb_df = run_sql_query(engine, "05_top10_comorbidities.sql", params=params)
    comorb_df = format_comorbidities(raw_comorb_df, top_n=10)
    comorb_df.to_csv(tables_dir / "top10_comorbidities.csv", index=False)
    comorb_fig, _ = plot_top_comorbidities(
        comorb_df,
        output_path=figures_dir / "top10_comorbidities.png",
    )
    plt.close(comorb_fig)

    print("[6/8] Plotting patient-averaged BMI...")
    raw_bmi_df = run_sql_query(engine, "06_patient_bmi.sql", params=params)
    patient_bmi_df = aggregate_patient_bmi(raw_bmi_df)
    patient_bmi_df.to_csv(tables_dir / "patient_averaged_bmi.csv", index=False)
    bmi_fig, _ = plot_bmi_distribution(
        patient_bmi_df,
        output_path=figures_dir / "bmi_distribution.png",
    )
    plt.close(bmi_fig)

    print("[7/8] Running CPAP persistence and Kaplan-Meier curve...")
    tte_df = run_sql_query(
        engine, "07_cpap_persistence_and_survival.sql", params=params
    )
    persistence_summary_df = summarize_cpap_persistence(tte_df)
    persistence_summary_df.to_csv(
        tables_dir / "cpap_persistence_summary.csv", index=False
    )
    cpap_km_fig, _ = plot_kaplan_meier_by_sex(
        tte_df[tte_df["initiated_pap"] == 1],
        duration_col="pap_persistence_days",
        event_col="pap_discontinued_event",
        title="Kaplan-Meier CPAP therapy persistence (30-day gap)",
        xlabel="Time since CPAP initiation (days)",
        ylabel="Persistence probability",
        output_path=figures_dir / "cpap_persistence_km.png",
    )
    plt.close(cpap_km_fig)

    print("[8/8] Plotting Kaplan-Meier by sex...")
    os_km_fig, _ = plot_kaplan_meier_by_sex(
        tte_df,
        duration_col="survival_days",
        event_col="death_event",
        title="Kaplan-Meier survival  post-OSA diagnosis",
        xlabel="Time since OSA diagnosis (days)",
        ylabel="Survival probability",
        output_path=figures_dir / "overall_survival_km.png",
    )
    plt.close(os_km_fig)

    print("done")


def main() -> None:
    engine = get_engine()
    run_pipeline(engine=engine)


if __name__ == "__main__":
    main()
