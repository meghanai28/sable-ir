#!/usr/bin/env python3
"""Generate the descriptive Stage 1 figure and source-data packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

DEFAULT_ROOT = Path("artifacts/stage1")
DEFAULT_OUTPUT = DEFAULT_ROOT / "figures/final"
SOURCE_PATHS = {
    "canonical_report_v2": DEFAULT_ROOT / "reports/stage1-report-v2.json",
    "primary_report": DEFAULT_ROOT / "reports/stage1-report.json",
    "natural_behavior": DEFAULT_ROOT / "reports/stage1-natural-behavior-20260904.json",
    "opposite_behavior": DEFAULT_ROOT / "reports/stage1-opposite-lean-behavior-20260904.json",
    "wrong_clause_behavior": DEFAULT_ROOT
    / "reports/stage1-wrong-clause-lean-behavior-20260904.json",
    "robustness_addendum": DEFAULT_ROOT / "reports/stage1-robustness-addendum-20260904.json",
    "length_report": DEFAULT_ROOT
    / "stage1a-plans-20260903-recovery3/analysis/stage1b-lengths.json",
    "plan_audit": DEFAULT_ROOT
    / "stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json",
}

TASK_ORDER = (
    "command_executable",
    "path_symlink_archive",
    "path_symlink_report",
    "sql_identifier",
    "ssrf_redirect",
)
TASK_LABELS = {
    "command_executable": "Command executable",
    "path_symlink_archive": "Symlink archive",
    "path_symlink_report": "Symlink report",
    "sql_identifier": "SQL identifier",
    "ssrf_redirect": "SSRF redirect",
}
FORMAT_ORDER = ("structured", "freeform")
CONCISION_ORDER = ("full", "concise", "minimal")
COLORS = {
    "blue": "#4E79A7",
    "orange": "#F28E2B",
    "red": "#E15759",
    "teal": "#76B7B2",
    "green": "#59A14F",
    "yellow": "#EDC948",
    "purple": "#B07AA1",
    "gray": "#9C9C9C",
    "dark": "#2F3742",
    "pale_green": "#DDEFD9",
    "pale_blue": "#DCE8F4",
}
PILOT_NOTE = (
    "Five-task behavioral study. Results are descriptive; tasks, not outputs, are the "
    "independent clusters."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sources() -> dict[str, dict[str, Any]]:
    sources = {name: load_json(path) for name, path in SOURCE_PATHS.items()}
    canonical = sources["canonical_report_v2"]
    primary = sources["primary_report"]
    robustness = sources["robustness_addendum"]
    if (
        canonical.get("status") != "complete"
        or canonical.get("recommendation") != "continue_to_stage2"
    ):
        raise ValueError("figures require the completed Stage 1 v2 report")
    if canonical.get("output_accounting", {}).get("total") != 852:
        raise ValueError("figures require the canonical 852-output Stage 1 accounting")
    if canonical.get("primary_stage1_report_sha256") != sha256(SOURCE_PATHS["primary_report"]):
        raise ValueError("canonical report does not bind the supplied primary report")
    if canonical.get("robustness_addendum_sha256") != sha256(SOURCE_PATHS["robustness_addendum"]):
        raise ValueError("canonical report does not bind the supplied robustness addendum")
    bound_hashes = {
        "natural_behavior": primary.get("natural_behavior_sha256"),
        "opposite_behavior": primary.get("opposite_behavior_sha256"),
        "wrong_clause_behavior": primary.get("wrong_clause_behavior_sha256"),
        "length_report": primary.get("length_report_sha256"),
        "plan_audit": primary.get("plan_audit_sha256"),
    }
    for name, expected_hash in bound_hashes.items():
        if expected_hash != sha256(SOURCE_PATHS[name]):
            raise ValueError(f"primary report hash mismatch for {name}")
    expected_rows = {
        "natural_behavior": 720,
        "opposite_behavior": 60,
        "wrong_clause_behavior": 24,
        "length_report": 180,
        "plan_audit": 180,
    }
    for name, count in expected_rows.items():
        if len(sources[name].get("rows", [])) != count:
            raise ValueError(f"expected {count} rows in {name}")
    if robustness.get("evaluated_clause_order_rows") != 24:
        raise ValueError("expected 24 evaluated clause-order rows")
    if robustness.get("evaluated_shuffled_rows") != 24:
        raise ValueError("expected 24 evaluated shuffled-task rows")
    return sources


def configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "legend.frameon": False,
            "svg.hashsalt": "sable-ir-stage1",
        }
    )


def save_figure(fig: Figure, output: Path, stem: str) -> list[Path]:
    fig.tight_layout(rect=(0, 0.045, 1, 0.97))
    png = output / f"{stem}.png"
    svg = output / f"{stem}.svg"
    fig.savefig(
        png,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Title": stem, "Author": "sable-ir", "Creation Time": None},
    )
    fig.savefig(
        svg,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Title": stem, "Creator": "sable-ir", "Date": None},
    )
    plt.close(fig)
    return [png, svg]


def add_note(fig: Figure, note: str = PILOT_NOTE) -> None:
    fig.text(0.01, 0.008, note, ha="left", va="bottom", fontsize=8, color="#555555")


def rate_label(ax: Axes, bar: Any, numerator: int, denominator: int) -> None:
    value = numerator / denominator
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.025,
        f"{value:.1%}\n({numerator}/{denominator})",
        ha="center",
        va="bottom",
        fontsize=9,
    )


def rate_label_inside(ax: Axes, bar: Any, numerator: int, denominator: int) -> None:
    value = numerator / denominator
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() - 0.025,
        f"{value:.1%}\n({numerator}/{denominator})",
        ha="center",
        va="top",
        fontsize=8,
        color="white",
        fontweight="bold",
    )


def rate_percent_inside(ax: Axes, bar: Any, numerator: int, denominator: int) -> None:
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() - 0.025,
        f"{numerator / denominator:.1%}",
        ha="center",
        va="top",
        fontsize=8,
        color="white",
        fontweight="bold",
    )


def assigned_policy_pass(row: dict[str, Any]) -> bool:
    field = "policy_a" if row["assigned_policy"] == "A" else "policy_b"
    return bool(row[field] == "pass")


def assigned_only(row: dict[str, Any]) -> bool:
    return bool(
        assigned_policy_pass(row)
        and row["policy_b" if row["assigned_policy"] == "A" else "policy_a"] == "fail"
    )


def opposite_only(row: dict[str, Any]) -> bool:
    opposite = "policy_b" if row["assigned_policy"] == "A" else "policy_a"
    assigned = "policy_a" if row["assigned_policy"] == "A" else "policy_b"
    return bool(row[opposite] == "pass" and row[assigned] == "fail")


def exact_reversal_rows(
    natural_rows: list[dict[str, Any]], opposite_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    natural_by_id = {row["job_id"]: row for row in natural_rows}
    eligible: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []
    for controlled in opposite_rows:
        natural = natural_by_id[controlled["job_id"]]
        jointly_functional = (
            natural["functionality"] == "pass" and controlled["functionality"] == "pass"
        )
        reversal = jointly_functional and assigned_only(natural) and opposite_only(controlled)
        row = {
            "job_id": controlled["job_id"],
            "task_id": controlled["task_id"],
            "assigned_policy": controlled["assigned_policy"],
            "jointly_functional": jointly_functional,
            "exact_reversal": reversal,
        }
        all_pairs.append(row)
        if jointly_functional:
            eligible.append(row)
    return all_pairs, eligible


def key_evidence(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    natural = sources["natural_behavior"]["rows"]
    opposite = sources["opposite_behavior"]["rows"]
    robustness = sources["robustness_addendum"]
    _all_pairs, eligible = exact_reversal_rows(natural, opposite)
    reversals = sum(row["exact_reversal"] for row in eligible)
    if (reversals, len(eligible)) != (50, 57):
        raise ValueError("canonical opposite-policy result is not 50/57")

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.5), gridspec_kw={"wspace": 0.38})

    ax = axes[0]
    reversal_rate = reversals / len(eligible)
    bar = ax.bar([0], [reversal_rate], width=0.58, color=COLORS["green"])[0]
    ax.axhline(0.20, color=COLORS["red"], linestyle="--", linewidth=1.8, label="Gate: ≥20%")
    rate_label(ax, bar, reversals, len(eligible))
    ax.set_title("A. Specific plan substitution")
    ax.set_ylabel("Exact behavioral reversal")
    ax.set_xticks([0], ["Assigned plan →\nopposite-policy plan"])
    ax.set_ylim(0, 1.12)
    ax.set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper left")
    ax.text(
        0.5,
        0.04,
        "Primary progression gate\n57 jointly functional pairs; floor = 40",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
        color="#555555",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2.5},
    )

    def paired_panel(
        panel: Axes,
        title: str,
        data: dict[str, Any],
        color: str,
        subtitle: str,
    ) -> None:
        samples = int(data["samples"])
        metrics = (
            (
                "Functional",
                int(data["natural_functional"]),
                int(data["controlled_functional"]),
            ),
            (
                "Assigned rule\n+ functional",
                int(data["natural_assigned_policy_and_functional"]),
                int(data["controlled_assigned_policy_and_functional"]),
            ),
        )
        x = np.arange(len(metrics))
        width = 0.34
        natural_values = [item[1] / samples for item in metrics]
        controlled_values = [item[2] / samples for item in metrics]
        natural_bars = panel.bar(
            x - width / 2,
            natural_values,
            width,
            color=COLORS["blue"],
            label="Natural plan",
        )
        controlled_bars = panel.bar(
            x + width / 2,
            controlled_values,
            width,
            color=color,
            label="Changed plan",
        )
        for index, item in enumerate(metrics):
            rate_label_inside(panel, natural_bars[index], item[1], samples)
            rate_label_inside(panel, controlled_bars[index], item[2], samples)
        panel.set_title(title)
        panel.set_xticks(x, [item[0] for item in metrics])
        panel.set_ylim(0, 1.15)
        panel.set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
        panel.grid(axis="y", alpha=0.22)
        panel.legend(loc="upper right", fontsize=8)
        panel.text(
            0.5,
            0.04,
            subtitle,
            transform=panel.transAxes,
            ha="center",
            va="bottom",
            fontsize=8,
            color="#555555",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2.5},
        )

    paired_panel(
        axes[1],
        "B. Benign clause reordering",
        robustness["clause_order"],
        COLORS["teal"],
        "Stable, as prospectively expected",
    )
    paired_panel(
        axes[2],
        "C. Wrong-task plan substitution",
        robustness["shuffled_task"],
        COLORS["orange"],
        "Disruptive, as prospectively expected",
    )
    fig.suptitle(
        "Stage 1: renderer behavior tracks visible-plan content", fontsize=19, fontweight="bold"
    )
    add_note(
        fig,
        "Panel A is the frozen primary gate. Panels B–C are post-primary controls whose "
        "design was frozen before their own outcomes; they have no numerical stop gate.",
    )
    source_rows = [
        {
            "panel": "specific_plan_substitution",
            "role": "primary_progression_gate",
            "metric": "exact_reversal_among_jointly_functional_pairs",
            "natural_numerator": "",
            "controlled_numerator": reversals,
            "denominator": len(eligible),
            "rate": reversal_rate,
        }
    ]
    for panel_name, payload in (
        ("clause_order", robustness["clause_order"]),
        ("shuffled_task", robustness["shuffled_task"]),
    ):
        for metric in ("functional", "assigned_policy_and_functional"):
            source_rows.append(
                {
                    "panel": panel_name,
                    "role": "post_primary_descriptive_robustness",
                    "metric": metric,
                    "natural_numerator": payload[f"natural_{metric}"],
                    "controlled_numerator": payload[f"controlled_{metric}"],
                    "denominator": payload["samples"],
                    "rate": payload[f"controlled_{metric}"] / payload["samples"],
                }
            )
    return save_figure(fig, output, "01-key-stage1-evidence"), source_rows


def natural_performance(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    rows = sources["natural_behavior"]["rows"]
    factors = (
        ("Assigned policy", "assigned_policy", ("A", "B")),
        ("Plan format", "plan_format", FORMAT_ORDER),
        ("Requested plan length", "nominal_concision", CONCISION_ORDER),
    )
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.6), gridspec_kw={"wspace": 0.34})
    source_rows: list[dict[str, Any]] = []
    for ax, (title, field, values) in zip(axes, factors, strict=True):
        x = np.arange(len(values))
        width = 0.35
        functional_counts: list[int] = []
        joint_counts: list[int] = []
        denominators: list[int] = []
        for value in values:
            subset = [row for row in rows if row[field] == value]
            denominator = len(subset)
            functional = sum(row["functionality"] == "pass" for row in subset)
            joint = sum(bool(row["assigned_policy_and_functional"]) for row in subset)
            denominators.append(denominator)
            functional_counts.append(functional)
            joint_counts.append(joint)
            source_rows.extend(
                [
                    {
                        "factor": field,
                        "level": value,
                        "metric": "functional",
                        "numerator": functional,
                        "denominator": denominator,
                        "rate": functional / denominator,
                    },
                    {
                        "factor": field,
                        "level": value,
                        "metric": "assigned_policy_and_functional",
                        "numerator": joint,
                        "denominator": denominator,
                        "rate": joint / denominator,
                    },
                ]
            )
        fbars = ax.bar(
            x - width / 2,
            np.array(functional_counts) / np.array(denominators),
            width,
            color=COLORS["blue"],
            label="Functional",
        )
        jbars = ax.bar(
            x + width / 2,
            np.array(joint_counts) / np.array(denominators),
            width,
            color=COLORS["green"],
            label="Assigned rule + functional",
        )
        for index, denominator in enumerate(denominators):
            rate_percent_inside(ax, fbars[index], functional_counts[index], denominator)
            rate_percent_inside(ax, jbars[index], joint_counts[index], denominator)
        labels = ["Free-form" if value == "freeform" else str(value).title() for value in values]
        ax.set_title(title)
        ax.set_xticks(x, labels)
        ax.set_ylim(0, 1.17)
        ax.set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
        ax.grid(axis="y", alpha=0.22)
        ax.legend(loc="lower left", fontsize=8)
    fig.suptitle("Natural renderer performance across Stage 1 design factors", fontsize=18)
    add_note(fig, "Natural renderer outputs only (n=720); four renders per generated plan.")
    return save_figure(fig, output, "02-natural-performance-by-factor"), source_rows


def reversal_by_group(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    all_pairs, eligible = exact_reversal_rows(
        sources["natural_behavior"]["rows"], sources["opposite_behavior"]["rows"]
    )
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"planned": 0, "eligible": 0, "reversals": 0}
    )
    for row in all_pairs:
        key = (row["task_id"], row["assigned_policy"])
        grouped[key]["planned"] += 1
        grouped[key]["eligible"] += int(row["jointly_functional"])
        grouped[key]["reversals"] += int(row["exact_reversal"])
    order = [(task, policy) for task in TASK_ORDER for policy in ("A", "B")]
    rates = [grouped[key]["reversals"] / grouped[key]["eligible"] for key in order]
    labels = [f"{TASK_LABELS[task]} — {policy}" for task, policy in order]
    colors = [COLORS["blue"] if policy == "A" else COLORS["teal"] for _task, policy in order]
    fig, ax = plt.subplots(figsize=(11.5, 7.4))
    y = np.arange(len(order))
    bars = ax.barh(y, rates, color=colors)
    overall_rate = sum(row["exact_reversal"] for row in eligible) / len(eligible)
    ax.axvline(
        overall_rate,
        color=COLORS["purple"],
        linestyle="--",
        linewidth=1.7,
        label="Overall: 50/57 (87.7%)",
    )
    for index, (bar, key) in enumerate(zip(bars, order, strict=True)):
        counts = grouped[key]
        ax.text(
            min(bar.get_width() + 0.018, 1.02),
            index,
            f"{counts['reversals']}/{counts['eligible']}",
            ha="left",
            va="center",
            fontsize=9,
        )
    ax.set_title("Exact opposite-policy reversal across all task-policy groups")
    ax.set_xlabel("Exact reversal among jointly functional pairs")
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1.12)
    ax.set_xticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.22)
    ax.legend(loc="lower right")
    add_note(
        fig,
        f"All 10/10 groups represented; {len(eligible)}/60 pairs were jointly functional. "
        "The gate is evaluated overall, not separately within each small group.",
    )
    source_rows = [
        {
            "task_id": task,
            "assigned_policy": policy,
            **grouped[(task, policy)],
            "reversal_rate_among_jointly_functional": grouped[(task, policy)]["reversals"]
            / grouped[(task, policy)]["eligible"],
        }
        for task, policy in order
    ]
    return save_figure(fig, output, "03-opposite-policy-reversal-by-group"), source_rows


def plan_length_distribution(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    rows = sources["length_report"]["rows"]
    data: list[list[int]] = []
    labels: list[str] = []
    colors: list[str] = []
    for concision in CONCISION_ORDER:
        for plan_format in FORMAT_ORDER:
            values = [
                int(row["plan_tokens"])
                for row in rows
                if row["nominal_concision"] == concision and row["plan_format"] == plan_format
            ]
            data.append(values)
            format_label = "Structured" if plan_format == "structured" else "Free-form"
            labels.append(f"{concision.title()}\n{format_label}")
            colors.append(COLORS["blue"] if plan_format == "structured" else COLORS["orange"])
    fig, ax = plt.subplots(figsize=(12, 6.7))
    boxes = ax.boxplot(
        data,
        patch_artist=True,
        widths=0.62,
        medianprops={"color": COLORS["dark"], "linewidth": 1.8},
        whiskerprops={"color": COLORS["dark"]},
        capprops={"color": COLORS["dark"]},
        flierprops={"marker": "o", "markersize": 3, "alpha": 0.45},
    )
    for box, color in zip(boxes["boxes"], colors, strict=True):
        box.set_facecolor(color)
        box.set_alpha(0.78)
    for position, values in enumerate(data, start=1):
        median = float(np.median(values))
        ax.text(position, median * 1.12, f"median {median:.0f}", ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylim(40, 1800)
    ax.set_ylabel("Exact visible-plan length in tokens (log scale)")
    ax.set_xticks(range(1, len(labels) + 1), labels)
    ax.set_title("Observed plan lengths by requested compression and format")
    ax.grid(axis="y", which="both", alpha=0.22)
    add_note(
        fig,
        "Length includes the transmitted END_PLAN sentinel; n=30 plans per box. Requested labels "
        "do not guarantee non-overlapping observed lengths.",
    )
    source_rows = [
        {
            key: row[key]
            for key in (
                "job_id",
                "task_id",
                "assigned_policy",
                "plan_format",
                "nominal_concision",
                "plan_sample_index",
                "plan_tokens",
                "secondary_content_tokens_without_labels_or_sentinel",
                "observed_length_bin",
            )
        }
        for row in rows
    ]
    return save_figure(fig, output, "04-plan-length-distributions"), source_rows


def outcome_heatmap(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    rows = sources["natural_behavior"]["rows"]
    columns = [
        (plan_format, concision) for plan_format in FORMAT_ORDER for concision in CONCISION_ORDER
    ]
    row_keys = [(task, policy) for task in TASK_ORDER for policy in ("A", "B")]
    matrix = np.zeros((len(row_keys), len(columns)))
    source_rows: list[dict[str, Any]] = []
    for row_index, (task, policy) in enumerate(row_keys):
        for col_index, (plan_format, concision) in enumerate(columns):
            subset = [
                row
                for row in rows
                if row["task_id"] == task
                and row["assigned_policy"] == policy
                and row["plan_format"] == plan_format
                and row["nominal_concision"] == concision
            ]
            successes = sum(bool(row["assigned_policy_and_functional"]) for row in subset)
            matrix[row_index, col_index] = successes / len(subset)
            source_rows.append(
                {
                    "task_id": task,
                    "assigned_policy": policy,
                    "plan_format": plan_format,
                    "nominal_concision": concision,
                    "successes": successes,
                    "denominator": len(subset),
                    "assigned_policy_and_functional_rate": successes / len(subset),
                }
            )
    fig, ax = plt.subplots(figsize=(11.7, 7.7))
    image = ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    ax.set_title("Assigned-policy-and-functional performance across natural conditions")
    ax.set_xticks(
        range(len(columns)),
        [
            f"{'Structured' if fmt == 'structured' else 'Free-form'}\n{length.title()}"
            for fmt, length in columns
        ],
    )
    ax.set_yticks(
        range(len(row_keys)),
        [f"{TASK_LABELS[task]} — {policy}" for task, policy in row_keys],
    )
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            ax.text(
                col_index,
                row_index,
                f"{value:.0%}\n({int(round(value * 12))}/12)",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value >= 0.72 else COLORS["dark"],
            )
    colorbar = fig.colorbar(image, ax=ax, shrink=0.8)
    colorbar.set_label("Assigned rule + functional rate")
    add_note(fig, "Each square contains 12 outputs: three planner samples × four renderer samples.")
    return save_figure(fig, output, "05-natural-condition-heatmap"), source_rows


def wrong_clause_control(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    natural_by_id = {row["job_id"]: row for row in sources["natural_behavior"]["rows"]}
    wrong_rows = sources["wrong_clause_behavior"]["rows"]
    pairs = [(natural_by_id[row["job_id"]], row) for row in wrong_rows]
    jointly_functional = [
        pair
        for pair in pairs
        if pair[0]["functionality"] == "pass" and pair[1]["functionality"] == "pass"
    ]
    values = {
        "functionality": (
            sum(a["functionality"] == "pass" for a, _b in pairs),
            sum(b["functionality"] == "pass" for _a, b in pairs),
            len(pairs),
        ),
        "conditional assigned-policy compliance": (
            sum(assigned_policy_pass(a) for a, _b in jointly_functional),
            sum(assigned_policy_pass(b) for _a, b in jointly_functional),
            len(jointly_functional),
        ),
    }
    if values != {
        "functionality": (23, 15, 24),
        "conditional assigned-policy compliance": (12, 5, 15),
    }:
        raise ValueError("wrong-clause summary disagrees with the canonical Stage 1 report")
    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    x = np.arange(2)
    width = 0.34
    natural_values = [item[0] / item[2] for item in values.values()]
    wrong_values = [item[1] / item[2] for item in values.values()]
    natural_bars = ax.bar(
        x - width / 2, natural_values, width, color=COLORS["blue"], label="Natural plan"
    )
    wrong_bars = ax.bar(
        x + width / 2, wrong_values, width, color=COLORS["purple"], label="Wrong-clause plan"
    )
    for index, item in enumerate(values.values()):
        rate_label(ax, natural_bars[index], item[0], item[2])
        rate_label(ax, wrong_bars[index], item[1], item[2])
    ax.set_title("Sampled wrong-clause control")
    ax.set_ylabel("Rate")
    ax.set_xticks(x, ["Functionality", "Assigned-rule compliance\namong jointly functional pairs"])
    ax.set_ylim(0, 1.14)
    ax.set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper right")
    add_note(
        fig,
        "Sampled descriptive negative control (24 frozen cells), not a progression gate. "
        "Functionality loss is reported separately from conditional policy behavior.",
    )
    source_rows = [
        {
            "metric": metric,
            "natural_numerator": counts[0],
            "controlled_numerator": counts[1],
            "denominator": counts[2],
            "natural_rate": counts[0] / counts[2],
            "controlled_rate": counts[1] / counts[2],
        }
        for metric, counts in values.items()
    ]
    return save_figure(fig, output, "06-wrong-clause-control"), source_rows


def audit_and_scope(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    audit_rows = sources["plan_audit"]["rows"]
    correct = sum(row["clause_selection"] == "correct" for row in audit_rows)
    retained = sum(row["policy_visibility"] == "preserved" for row in audit_rows)
    no_irrelevant = sum(not row["irrelevant_clause_ids_included"] for row in audit_rows)
    gate_s17 = next(
        gate for gate in sources["primary_report"]["gates"] if gate["gate_id"] == "S1.7"
    )
    supported_bins = int(gate_s17["observed"])
    if (correct, retained, no_irrelevant, supported_bins) != (180, 180, 180, 1):
        raise ValueError("plan-audit or compression-scope values differ from the frozen report")
    fig, (left, right) = plt.subplots(1, 2, figsize=(12.8, 5.8), gridspec_kw={"wspace": 0.38})
    labels = (
        "Correct clause\nselected",
        "A/B distinction\nretained",
        "No irrelevant\nclause included",
    )
    numerators = (correct, retained, no_irrelevant)
    bars = left.bar(
        range(3),
        [value / 180 for value in numerators],
        color=[COLORS["blue"], COLORS["green"], COLORS["teal"]],
    )
    for bar, numerator in zip(bars, numerators, strict=True):
        rate_label(left, bar, numerator, 180)
    left.set_title("Behavior-blinded natural-plan audit")
    left.set_xticks(range(3), labels)
    left.set_ylim(0, 1.15)
    left.set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
    left.grid(axis="y", alpha=0.22)

    right.axhspan(0, 1, color=COLORS["pale_blue"], alpha=0.7)
    right.axhspan(1, 2, color=COLORS["pale_green"], alpha=0.7)
    right.axhspan(2, 3.35, color="#F6E7C7", alpha=0.65)
    bar = right.bar([0], [supported_bins], width=0.48, color=COLORS["purple"])[0]
    right.text(
        bar.get_x() + bar.get_width() / 2,
        1.08,
        "1 supported bin",
        ha="center",
        fontsize=11,
        fontweight="bold",
    )
    right.axhline(1, color=COLORS["dark"], linewidth=1.2)
    right.axhline(2, color=COLORS["dark"], linewidth=1.2, linestyle="--")
    right.axhline(3, color=COLORS["dark"], linewidth=1.2, linestyle=":")
    right.text(0.27, 0.52, "Format comparison supported", transform=right.transAxes, fontsize=9)
    right.text(0.27, 0.72, "Compression trend requires ≥2", transform=right.transAxes, fontsize=9)
    right.text(0.27, 0.92, "Nonlinear/crossover requires ≥3", transform=right.transAxes, fontsize=9)
    right.set_title("Evidence scope from strict length matching")
    right.set_ylabel("Number of supported length bins")
    right.set_xticks([0], ["Observed support"])
    right.set_ylim(0, 3.35)
    right.set_yticks([0, 1, 2, 3])
    add_note(
        fig,
        "The sole supported bin contained 13 strict structured/free-form matches spanning 8/10 "
        "task-policy groups; compression was tested, but no trend claim is supported.",
    )
    source_rows = [
        {
            "section": "plan_audit",
            "metric": "correct_clause_selection",
            "numerator": correct,
            "denominator": 180,
        },
        {
            "section": "plan_audit",
            "metric": "policy_visibility_preserved",
            "numerator": retained,
            "denominator": 180,
        },
        {
            "section": "plan_audit",
            "metric": "no_irrelevant_clause_included",
            "numerator": no_irrelevant,
            "denominator": 180,
        },
        {
            "section": "length_evidence",
            "metric": "supported_bins",
            "numerator": supported_bins,
            "denominator": "not_applicable",
        },
        {
            "section": "length_evidence",
            "metric": "strict_matches_in_supported_bin",
            "numerator": 13,
            "denominator": "not_applicable",
        },
        {
            "section": "length_evidence",
            "metric": "task_policy_groups_in_supported_bin",
            "numerator": 8,
            "denominator": 10,
        },
    ]
    return save_figure(fig, output, "07-plan-audit-and-compression-scope"), source_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing empty CSV: {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(output: Path) -> Path:
    path = output / "README.md"
    path.write_text(
        "# Stage 1 final figures\n\n"
        "These figures summarize the canonical Stage 1 v2 evidence packet (852 code outputs). "
        "The primary progression gate was frozen before its outcomes. Clause-order and "
        "shuffled-task controls were added after the primary result, but their design was frozen "
        "before their own outcomes; they remain supporting descriptive robustness evidence.\n\n"
        "## Figures\n\n"
        "1. Key evidence: exact opposite-policy reversal, clause-order stability, and "
        "wrong-task disruption.\n"
        "2. Natural renderer performance across assigned policy, plan format, and requested "
        "length.\n"
        "3. Exact opposite-policy reversals across all ten task-policy groups.\n"
        "4. Exact visible-plan length distributions, including `END_PLAN`.\n"
        "5. Natural assigned-policy-and-functional rates across the 60 design conditions.\n"
        "6. Sampled wrong-clause negative control, with functionality reported separately.\n"
        "7. Behavior-blinded plan audit and the supported scope of the compression analysis.\n\n"
        "Each figure is emitted as a 300-DPI PNG and editable SVG. CSV files contain the plotted "
        "values. `figure-manifest.json` records SHA-256 hashes for every source and output.\n\n"
        "The plots support behavioral claims only. They do not establish mediation or any internal "
        "mechanism. One supported length bin permits a format comparison, not a general "
        "compression "
        "trend or nonlinear/crossover claim.\n\n"
        "Regenerate from the repository root with:\n\n"
        "```bash\n"
        "uv run --extra plots python scripts/plot_stage1_results.py\n"
        "```\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    args = parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    sources = load_sources()

    generated: list[Path] = []
    csv_payloads: dict[str, list[dict[str, Any]]] = {}
    figure_builders = (
        ("key-evidence.csv", key_evidence),
        ("natural-performance-by-factor.csv", natural_performance),
        ("opposite-policy-reversal-by-group.csv", reversal_by_group),
        ("plan-lengths.csv", plan_length_distribution),
        ("natural-condition-heatmap.csv", outcome_heatmap),
        ("wrong-clause-control.csv", wrong_clause_control),
        ("plan-audit-and-compression-scope.csv", audit_and_scope),
    )
    for csv_name, builder in figure_builders:
        figure_files, rows = builder(sources, output)
        generated.extend(figure_files)
        csv_payloads[csv_name] = rows
    for name, rows in csv_payloads.items():
        path = output / name
        write_csv(path, rows)
        generated.append(path)
    generated.append(write_readme(output))

    manifest_path = output / "figure-manifest.json"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "canonical_status": sources["canonical_report_v2"]["status"],
        "canonical_recommendation": sources["canonical_report_v2"]["recommendation"],
        "code_output_accounting": sources["canonical_report_v2"]["output_accounting"],
        "behavioral_only": True,
        "independent_task_clusters": 5,
        "sources": [
            {
                "name": name,
                "path": path.as_posix(),
                "sha256": sha256(path.resolve()),
            }
            for name, path in SOURCE_PATHS.items()
        ],
        "files": [
            {"path": path.relative_to(output).as_posix(), "sha256": sha256(path)}
            for path in sorted(generated)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(generated)} files plus manifest in {output}")


if __name__ == "__main__":
    os.environ.setdefault("SOURCE_DATE_EPOCH", "1788532800")
    main()
