from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from osa_epi.analysis import (
    compute_kaplan_meier,
    compute_logrank_test,
    summarize_continuous,
)

SEX_PALETTE = {
    "MALE": "#2b5c8f",
    "FEMALE": "#c85a32",
    "UNKNOWN": "#6c757d",
}


def plot_age_distribution_by_sex(
    df: pd.DataFrame,
    bin_width: int = 5,
    output_path: Path | None = None,
) -> tuple[Figure, np.ndarray]:
    """Plot shared-axis age histograms with median and iqr overlays per sex"""
    sexes = sorted(df["sex"].unique())
    min_edge = np.floor(df["age_at_index"].min() / bin_width) * bin_width
    max_edge = np.ceil(df["age_at_index"].max() / bin_width) * bin_width + bin_width
    bins = np.arange(min_edge, max_edge, bin_width)

    sns.set_theme(style="whitegrid", context="notebook")
    fig, axes = plt.subplots(
        1,
        len(sexes),
        figsize=(6 * len(sexes), 4.8),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    flat_axes = axes.ravel()

    for ax, sex in zip(flat_axes, sexes):
        subset = df[df["sex"] == sex]
        color = SEX_PALETTE.get(sex, "#4c72b0")

        sns.histplot(
            data=subset,
            x="age_at_index",
            bins=bins,
            kde=len(subset) > 1,
            color=color,
            edgecolor="white",
            alpha=0.75,
            ax=ax,
        )

        stats = summarize_continuous(subset["age_at_index"])
        ax.axvline(
            stats["median"],
            color="#111111",
            linestyle="--",
            linewidth=1.6,
            label=f"Median: {stats['median']:.1f} yrs",
        )
        ax.axvspan(
            stats["q25"],
            stats["q75"],
            color=color,
            alpha=0.12,
            label=f"IQR: {stats['q25']:.1f} - {stats['q75']:.1f}",
        )

        ax.set_title(
            f"{sex.title()} (n = {len(subset)})", fontsize=12, fontweight="bold"
        )
        ax.set_xlabel("Age at OSA Index Diagnosis (years)")
        ax.legend(frameon=True, fontsize=9.5)

    flat_axes[0].set_ylabel("Number of Patients")
    fig.suptitle(
        "OSA patients age distribution by sex",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    sns.despine()
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig, flat_axes


def plot_top_comorbidities(
    df: pd.DataFrame,
    output_path: Path | None = None,
) -> tuple[Figure, Axes]:
    """Plot a horizontal bar chart of top baseline comorbidities with counts and %."""
    sns.set_theme(style="whitegrid", context="notebook")
    fig_height = max(4.2, 0.52 * len(df) + 1.4)
    fig, ax = plt.subplots(figsize=(9.5, fig_height))

    sns.barplot(
        data=df,
        x="patient_count",
        y="concept_name",
        hue="concept_name",
        palette="viridis_r",
        legend=False,
        edgecolor="white",
        ax=ax,
    )

    max_count = df["patient_count"].max() if not df.empty else 1
    offset = max_count * 0.015
    for idx, row in df.iterrows():
        label = row.get(
            "bar_label",
            f"{int(row['patient_count'])} ({row['prevalence_pct']:.1f}%)",
        )
        ax.text(
            row["patient_count"] + offset,
            idx,
            label,
            va="center",
            ha="left",
            fontsize=9.5,
            color="#222222",
        )

    ax.set_xlim(0, max_count * 1.22)
    ax.set_xlabel("Number of patients (% of cohort)")
    ax.set_ylabel("")
    ax.set_title(
        f"Top {len(df)} comorbidities at OSA Diagnosis",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    sns.despine()
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig, ax


def plot_bmi_distribution(
    df: pd.DataFrame,
    bin_width: float = 2.0,
    output_path: Path | None = None,
) -> tuple[Figure, Axes]:
    """Plot patient-averaged BMI histogram by sex"""
    plot_df = df.copy()
    if "sex" not in plot_df.columns:
        plot_df["sex"] = "UNKNOWN"
    plot_df["sex"] = plot_df["sex"].fillna("Unknown").str.upper()

    sexes = sorted(plot_df["sex"].unique())
    palette = {sex: SEX_PALETTE.get(sex, "#4c72b0") for sex in sexes}

    min_edge = np.floor(plot_df["mean_bmi"].min() / bin_width) * bin_width
    max_edge = np.ceil(plot_df["mean_bmi"].max() / bin_width) * bin_width + bin_width
    if max_edge <= min_edge:
        max_edge = min_edge + bin_width
    bins = np.arange(min_edge, max_edge, bin_width)

    sns.set_theme(style="whitegrid", context="notebook")
    fig, ax = plt.subplots(figsize=(8.8, 5.0))

    sns.histplot(
        data=plot_df,
        x="mean_bmi",
        hue="sex",
        hue_order=sexes,
        palette=palette,
        bins=bins,
        kde=len(plot_df) > 1,
        common_norm=False,
        element="bars",
        alpha=0.45,
        edgecolor="white",
        ax=ax,
    )

    for sex in sexes:
        subset = plot_df[plot_df["sex"] == sex]
        stats = summarize_continuous(subset["mean_bmi"])
        color = palette[sex]
        ax.axvline(
            stats["median"],
            color=color,
            linestyle="--",
            linewidth=1.8,
            label=(
                f"{sex.title()} (n={len(subset)}) median: "
                f"{stats['median']:.1f} (IQR {stats['q25']:.1f} - {stats['q75']:.1f})"
            ),
        )

    ax.axvline(
        25.0,
        color="#d97706",
        linestyle=":",
        linewidth=1.5,
        label="Overweight (25 kg/m2)",
    )
    ax.axvline(
        30.0,
        color="#b91c1c",
        linestyle=":",
        linewidth=1.5,
        label="Obesity (30 kg/m2)",
    )

    ax.set_xlabel("Patient-averaged baseline BMI (kg/m2)")
    ax.set_ylabel("Number of patients")
    ax.set_title(
        "Patient BMI by sex",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.legend(frameon=True, fontsize=9.0)
    sns.despine()
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig, ax


def plot_kaplan_meier_by_sex(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path | None = None,
) -> tuple[Figure, Axes]:
    """Plot kaplan-meier"""
    plot_df = df[[duration_col, event_col, "sex"]].dropna().copy()
    plot_df["sex"] = plot_df["sex"].fillna("Unknown").str.upper()
    sexes = sorted(plot_df["sex"].unique())

    sns.set_theme(style="whitegrid", context="notebook")
    fig, ax = plt.subplots(figsize=(8.8, 5.2))

    for sex in sexes:
        subset = plot_df[plot_df["sex"] == sex]
        color = SEX_PALETTE.get(sex, "#4c72b0")
        km = compute_kaplan_meier(subset[duration_col], subset[event_col])
        n_events = int(subset[event_col].sum())

        ax.step(
            km["time"],
            km["survival"],
            where="post",
            color=color,
            linewidth=2.0,
            label=f"{sex.title()} (n = {len(subset)}, events = {n_events})",
        )
        ax.fill_between(
            km["time"],
            km["ci_lower"],
            km["ci_upper"],
            step="post",
            color=color,
            alpha=0.14,
        )

        censored_times = subset.loc[subset[event_col] == 0, duration_col].to_numpy(
            dtype=float
        )
        if censored_times.size > 0 and not km.empty:
            km_times = km["time"].to_numpy()
            km_surv = km["survival"].to_numpy()
            idx = np.clip(
                np.searchsorted(km_times, censored_times, side="right") - 1,
                0,
                len(km_surv) - 1,
            )
            ax.scatter(
                censored_times,
                km_surv[idx],
                marker="+",
                s=34,
                color=color,
                alpha=0.85,
                zorder=4,
            )

    lr = compute_logrank_test(
        plot_df,
        duration_col=duration_col,
        event_col=event_col,
        group_col="sex",
    )
    if not np.isnan(lr["p_value"]):
        p_text = (
            "Log-rank p < 0.001"
            if lr["p_value"] < 0.001
            else f"Log-rank chi2 = {lr['chi2']:.2f}, p = {lr['p_value']:.3f}"
        )
        ax.text(
            0.03,
            0.06,
            p_text,
            transform=ax.transAxes,
            fontsize=9.5,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.85},
        )

    ax.set_xlim(left=0)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.legend(frameon=True, fontsize=9.5, loc="upper right")
    sns.despine()
    fig.tight_layout()

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return fig, ax
