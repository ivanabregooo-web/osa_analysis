import numpy as np
import pandas as pd
from scipy.stats import chi2


def prepare_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute age at index diagnosis and follow-up duration in days"""
    required = {
        "person_id",
        "cohort_start_date",
        "cohort_end_date",
        "year_of_birth",
        "sex",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    out["cohort_start_date"] = pd.to_datetime(out["cohort_start_date"])
    out["cohort_end_date"] = pd.to_datetime(out["cohort_end_date"])

    out["age_at_index"] = out["cohort_start_date"].dt.year - out["year_of_birth"]
    out["followup_days"] = (out["cohort_end_date"] - out["cohort_start_date"]).dt.days
    out["sex"] = out["sex"].fillna("Unknown").str.upper()
    return out


def summarize_continuous(series: pd.Series) -> dict[str, float]:
    """Return median and interquartile range (q25, q75)"""
    clean = series.dropna().to_numpy()
    if clean.size == 0:
        return {"median": np.nan, "q25": np.nan, "q75": np.nan}
    q25, median, q75 = np.percentile(clean, [25, 50, 75])
    return {"median": float(median), "q25": float(q25), "q75": float(q75)}


def format_comorbidities(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Sort comorbidities by patient count and build display labels."""
    required = {"concept_name", "patient_count", "prevalence_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = (
        df.sort_values(
            by=["patient_count", "concept_name"],
            ascending=[False, True],
        )
        .head(top_n)
        .copy()
    )
    out["bar_label"] = out.apply(
        lambda r: f"{int(r['patient_count'])} ({r['prevalence_pct']:.1f}%)",
        axis=1,
    )
    return out.reset_index(drop=True)


def aggregate_patient_bmi(df: pd.DataFrame) -> pd.DataFrame:
    """Average BMI measurements per patient"""
    required = {"person_id", "bmi"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    clean = df.dropna(subset=["bmi"]).copy()
    if "sex" in clean.columns:
        clean["sex"] = clean["sex"].fillna("Unknown").str.upper()
        grouped = (
            clean.groupby(["person_id", "sex"], as_index=False)
            .agg(
                mean_bmi=("bmi", "mean"),
                n_measurements=("bmi", "count"),
            )
            .sort_values("person_id")
            .reset_index(drop=True)
        )
    else:
        grouped = (
            clean.groupby("person_id", as_index=False)
            .agg(
                mean_bmi=("bmi", "mean"),
                n_measurements=("bmi", "count"),
            )
            .sort_values("person_id")
            .reset_index(drop=True)
        )
    return grouped


def compute_kaplan_meier(
    durations: pd.Series | np.ndarray,
    events: pd.Series | np.ndarray,
) -> pd.DataFrame:
    """Compute kaplan-meier survival curve with greenwood 95% CI"""
    t = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    valid = ~np.isnan(t)
    t = t[valid]
    e = e[valid]

    if t.size == 0:
        return pd.DataFrame(
            columns=["time", "n_risk", "n_events", "survival", "ci_lower", "ci_upper"]
        )

    rows = [
        {
            "time": 0.0,
            "n_risk": int(t.size),
            "n_events": 0,
            "survival": 1.0,
            "ci_lower": 1.0,
            "ci_upper": 1.0,
        }
    ]

    event_times = np.unique(t[e == 1])
    surv = 1.0
    greenwood_sum = 0.0
    z = 1.959963984540054

    for et in event_times:
        if et == 0.0:
            n_risk = int(np.sum(t >= 0.0))
            n_events = int(np.sum((t == 0.0) & (e == 1)))
            surv *= 1.0 - (n_events / n_risk)
            if n_risk > n_events:
                greenwood_sum += n_events / (n_risk * (n_risk - n_events))
            se = surv * np.sqrt(greenwood_sum)
            rows[0] = {
                "time": 0.0,
                "n_risk": n_risk,
                "n_events": n_events,
                "survival": float(surv),
                "ci_lower": float(np.clip(surv - z * se, 0.0, 1.0)),
                "ci_upper": float(np.clip(surv + z * se, 0.0, 1.0)),
            }
            continue

        n_risk = int(np.sum(t >= et))
        n_events = int(np.sum((t == et) & (e == 1)))
        surv *= 1.0 - (n_events / n_risk)
        if n_risk > n_events:
            greenwood_sum += n_events / (n_risk * (n_risk - n_events))
        se = surv * np.sqrt(greenwood_sum)
        rows.append(
            {
                "time": float(et),
                "n_risk": n_risk,
                "n_events": n_events,
                "survival": float(surv),
                "ci_lower": float(np.clip(surv - z * se, 0.0, 1.0)),
                "ci_upper": float(np.clip(surv + z * se, 0.0, 1.0)),
            }
        )

    max_time = float(np.max(t))
    if max_time > rows[-1]["time"]:
        last = rows[-1]
        rows.append(
            {
                "time": max_time,
                "n_risk": int(np.sum(t >= max_time)),
                "n_events": 0,
                "survival": last["survival"],
                "ci_lower": last["ci_lower"],
                "ci_upper": last["ci_upper"],
            }
        )

    return pd.DataFrame(rows)


def survival_at_times(
    km_df: pd.DataFrame,
    time_points: tuple[float, ...] = (90.0, 180.0, 365.0, 730.0),
) -> dict[float, float]:
    """Evaluate step-function Kaplan-Meier survival probability"""
    if km_df.empty:
        return {float(tp): np.nan for tp in time_points}

    times = km_df["time"].to_numpy()
    surv = km_df["survival"].to_numpy()
    max_obs = float(times[-1])
    out: dict[float, float] = {}
    for tp in time_points:
        tp_f = float(tp)
        if tp_f > max_obs and surv[-1] > 0.0:
            out[tp_f] = np.nan
            continue
        idx = int(np.searchsorted(times, tp_f, side="right")) - 1
        idx = max(0, min(idx, len(surv) - 1))
        out[tp_f] = float(surv[idx])
    return out


def compute_logrank_test(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
    group_col: str = "sex",
) -> dict[str, float]:
    """Perform a log-rank test"""
    clean = df[[duration_col, event_col, group_col]].dropna().copy()
    groups = sorted(clean[group_col].unique())
    if len(groups) < 2:
        return {"chi2": np.nan, "df": 0, "p_value": np.nan}

    t = clean[duration_col].to_numpy(dtype=float)
    e = clean[event_col].to_numpy(dtype=int)
    g = clean[group_col].to_numpy()

    event_times = np.unique(t[e == 1])
    k = len(groups)
    obs_minus_exp = np.zeros(k, dtype=float)
    cov_matrix = np.zeros((k, k), dtype=float)

    for et in event_times:
        at_risk_mask = t >= et
        n_total = float(np.sum(at_risk_mask))
        if n_total <= 1.0:
            continue
        d_total = float(np.sum(at_risk_mask & (t == et) & (e == 1)))

        n_g = np.array(
            [np.sum(at_risk_mask & (g == grp)) for grp in groups],
            dtype=float,
        )
        d_g = np.array(
            [np.sum((t == et) & (e == 1) & (g == grp)) for grp in groups],
            dtype=float,
        )

        e_g = n_g * (d_total / n_total)
        obs_minus_exp += d_g - e_g

        factor = (d_total * (n_total - d_total)) / (n_total * n_total * (n_total - 1.0))
        for i in range(k):
            for j in range(k):
                delta = 1.0 if i == j else 0.0
                cov_matrix[i, j] += n_g[i] * (delta - n_g[j] / n_total) * factor

    u_sub = obs_minus_exp[:-1]
    v_sub = cov_matrix[:-1, :-1]
    v_inv = np.linalg.pinv(v_sub)
    chi2_stat = float(u_sub @ v_inv @ u_sub)
    dof = k - 1
    p_val = float(chi2.sf(chi2_stat, df=dof))
    return {"chi2": chi2_stat, "df": dof, "p_value": p_val}


def summarize_cpap_persistence(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize CPAP initiation and persistence by sex"""
    clean = df.copy()
    clean["sex"] = clean["sex"].fillna("Unknown").str.upper()

    strata: list[tuple[str, pd.DataFrame]] = [("OVERALL", clean)]
    for sex in sorted(clean["sex"].unique()):
        strata.append((sex, clean[clean["sex"] == sex]))

    rows = []
    for label, sub in strata:
        n_total = len(sub)
        initiators = sub[sub["initiated_pap"] == 1]
        n_init = len(initiators)
        init_pct = round(100.0 * n_init / n_total, 1) if n_total > 0 else np.nan

        n_disc = int(initiators["pap_discontinued_event"].sum()) if n_init > 0 else 0
        disc_pct = round(100.0 * n_disc / n_init, 1) if n_init > 0 else np.nan

        delay_stats = summarize_continuous(initiators["days_to_pap_initiation"])
        pers_stats = summarize_continuous(initiators["pap_persistence_days"])
        km = compute_kaplan_meier(
            initiators["pap_persistence_days"],
            initiators["pap_discontinued_event"],
        )
        landmarks = survival_at_times(km, (90.0, 180.0, 365.0, 730.0))

        rows.append(
            {
                "stratum": label,
                "cohort_n": n_total,
                "cpap_initiators_n": n_init,
                "cpap_initiation_pct": init_pct,
                "discontinued_n": n_disc,
                "discontinued_pct": disc_pct,
                "median_days_to_initiation": round(delay_stats["median"], 1),
                "median_persistence_days": round(pers_stats["median"], 1),
                "persistence_iqr_low": round(pers_stats["q25"], 1),
                "persistence_iqr_high": round(pers_stats["q75"], 1),
                "km_persist_90d_pct": round(landmarks[90.0] * 100.0, 1),
                "km_persist_180d_pct": round(landmarks[180.0] * 100.0, 1),
                "km_persist_365d_pct": round(landmarks[365.0] * 100.0, 1),
                "km_persist_730d_pct": round(landmarks[730.0] * 100.0, 1),
            }
        )

    return pd.DataFrame(rows)
