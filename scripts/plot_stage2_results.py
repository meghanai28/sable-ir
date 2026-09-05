#!/usr/bin/env python3
"""Generate the descriptive Stage 2 figure and source-data packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

DEFAULT_ROOT = Path("artifacts/stage2")
DEFAULT_OUTPUT = DEFAULT_ROOT / "figures/final"
SOURCE_PATHS = {
    "stage1_primary_report": Path("artifacts/stage1/reports/stage1-report.json"),
    "dataset_manifest": DEFAULT_ROOT / "dataset/manifest.json",
    "training_result": DEFAULT_ROOT / "training/sft-01/training-result.json",
    "checkpoint_selection": DEFAULT_ROOT / "selection.json",
    "dev_18_final": DEFAULT_ROOT / "eval/dev-18/report-final-stage1-passed.json",
    "dev_36_final": DEFAULT_ROOT / "eval/dev-36/report-final-stage1-passed.json",
    "dev_54_final": DEFAULT_ROOT / "eval/dev-54/report-final-stage1-passed.json",
    "model_floor_final": DEFAULT_ROOT / "eval/floor-01/report-final-stage1-passed.json",
    "test_manifest": DEFAULT_ROOT / "eval/test-01/manifest.json",
    "test_plan_audit": DEFAULT_ROOT / "eval/test-01/plan-audit.json",
    "test_final": DEFAULT_ROOT / "eval/test-01/report-final-stage1-passed.json",
}

FORMAT_CONCISION_ORDER = (
    "structured/full",
    "structured/concise",
    "structured/minimal",
    "freeform/full",
    "freeform/concise",
    "freeform/minimal",
)
CELL_LABELS = {
    "structured/full": "Structured\nFull",
    "structured/concise": "Structured\nConcise",
    "structured/minimal": "Structured\nMinimal",
    "freeform/full": "Free-form\nFull",
    "freeform/concise": "Free-form\nConcise",
    "freeform/minimal": "Free-form\nMinimal",
}
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
}
PILOT_NOTE = (
    "Five-task pilot with a 3/1/1 base-task split; dev and test estimates each come from one "
    "task and do not support population-level generalization."
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
    stage1_hash = sha256(SOURCE_PATHS["stage1_primary_report"])
    for name in (
        "dev_18_final",
        "dev_36_final",
        "dev_54_final",
        "model_floor_final",
        "test_final",
    ):
        report = sources[name]
        if report.get("stage1_gate") != "passed":
            raise ValueError(f"{name} is not finalized against a passed Stage 1 gate")
        if report.get("stage1_report_sha256") != stage1_hash:
            raise ValueError(f"{name} does not bind the current Stage 1 primary report")
        if report.get("stage2_status") != "valid_continuation":
            raise ValueError(f"{name} is not a valid Stage 2 continuation")
        if report.get("complete") is not True:
            raise ValueError(f"{name} is incomplete")
        if report.get("invalid_task_or_tests") is True:
            raise ValueError(f"{name} detected invalid mutually exclusive policy tests")

    floor = sources["model_floor_final"]
    if floor.get("kind") != "model_floor" or floor["model_floor"].get("passed") is not True:
        raise ValueError("the finalized model-floor report did not pass")
    if floor["model_floor"].get("recommendation") != "continue_with_primary_model":
        raise ValueError("the finalized model-floor recommendation changed")

    selection = sources["checkpoint_selection"]
    training = sources["training_result"]
    if selection.get("training_result_sha256") != sha256(SOURCE_PATHS["training_result"]):
        raise ValueError("checkpoint selection does not bind the training result")
    selected = selection["selected_adapter"]
    if selected.get("global_step") != 36:
        raise ValueError("the selected Stage 2 checkpoint is not step 36")
    if sources["test_manifest"].get("checkpoint_selection_sha256") != sha256(
        SOURCE_PATHS["checkpoint_selection"]
    ):
        raise ValueError("test manifest does not bind the selected checkpoint")
    if sources["test_final"].get("plan_audit_sha256") != sha256(SOURCE_PATHS["test_plan_audit"]):
        raise ValueError("test report does not bind the completed plan audit")
    if sources["test_final"].get("eval_manifest_sha256") != sha256(SOURCE_PATHS["test_manifest"]):
        raise ValueError("test report does not bind the test manifest")
    if sources["test_final"]["planner_adapter"]["directory"] != selected["directory"]:
        raise ValueError("test report did not use the dev-selected adapter")

    expected_metrics = {18: 0.1042, 36: 0.1875, 54: 0.1667}
    for step, source_name in ((18, "dev_18_final"), (36, "dev_36_final"), (54, "dev_54_final")):
        report = sources[source_name]
        if report.get("selection_metric_value") != expected_metrics[step]:
            raise ValueError(f"unexpected checkpoint-{step} selection metric")
        candidate = selection["candidates"][
            f"artifacts/stage2/training/sft-01/checkpoints/checkpoint-{step}"
        ]
        if candidate != report["selection_metric_value"]:
            raise ValueError(f"finalized dev-{step} metric differs from frozen selection")

    test = sources["test_final"]
    if len(test.get("rows", [])) != 144 or len(test.get("direct_rows", [])) != 24:
        raise ValueError("the test report does not contain the frozen 144 render + 24 direct rows")
    if len(sources["test_plan_audit"].get("rows", [])) != 36:
        raise ValueError("the completed test audit does not contain 36 plans")
    if training.get("status") != "awaiting_dev_checkpoint_selection":
        raise ValueError("unexpected immutable training-result status")
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
            "svg.hashsalt": "sable-ir-stage2",
        }
    )


def save_figure(fig: Figure, output: Path, stem: str) -> list[Path]:
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
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
    fig.text(0.01, 0.009, note, ha="left", va="bottom", fontsize=8, color="#555555")


def label_bar(
    ax: Axes,
    bar: Any,
    value: float,
    numerator: int | None = None,
    denominator: int | None = None,
    *,
    inside: bool = False,
) -> None:
    text = f"{value:.1%}"
    if numerator is not None and denominator is not None:
        text += f"\n({numerator}/{denominator})"
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() - 0.025 if inside else bar.get_height() + 0.025,
        text,
        ha="center",
        va="top" if inside else "bottom",
        fontsize=8.5,
        color="white" if inside else "black",
        fontweight="bold" if inside else "normal",
    )


def key_evidence(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    floor = sources["model_floor_final"]["model_floor"]
    selection = sources["checkpoint_selection"]
    test = sources["test_final"]
    test_task = test["by_task"]["path_symlink_archive"]
    audit_rows = sources["test_plan_audit"]["rows"]

    fig, axes = plt.subplots(1, 3, figsize=(14.6, 5.6), gridspec_kw={"wspace": 0.38})
    source_rows: list[dict[str, Any]] = []

    floor_labels = ("Direct\nfull document", "Reference\nstructured", "Reference\nfree-form")
    floor_values = (
        float(floor["full_document_direct_assigned_and_functional"]),
        float(floor["reference_plan_structured_assigned_and_functional"]),
        float(floor["reference_plan_freeform_assigned_and_functional"]),
    )
    floor_counts = ((14, 32), (20, 32), (22, 32))
    bars = axes[0].bar(
        range(3), floor_values, color=[COLORS["blue"], COLORS["green"], COLORS["teal"]]
    )
    axes[0].axhline(0.30, color=COLORS["red"], linestyle="--", linewidth=1.7, label="Floor: ≥30%")
    for bar, value, counts in zip(bars, floor_values, floor_counts, strict=True):
        label_bar(axes[0], bar, value, *counts)
    axes[0].set_title("A. Model-floor capability")
    axes[0].set_xticks(range(3), floor_labels)
    axes[0].set_ylim(0, 0.83)
    axes[0].set_yticks(np.arange(0, 0.81, 0.2), [f"{x:.0%}" for x in np.arange(0, 0.81, 0.2)])
    axes[0].set_ylabel("Assigned rule + functional")
    axes[0].grid(axis="y", alpha=0.22)
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].text(
        0.5,
        0.04,
        "PASSED · continue with 4B model",
        transform=axes[0].transAxes,
        ha="center",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2.5},
    )
    for label, value, counts in zip(floor_labels, floor_values, floor_counts, strict=True):
        source_rows.append(
            {
                "panel": "model_floor",
                "metric": label.replace("\n", " "),
                "numerator": counts[0],
                "denominator": counts[1],
                "rate": value,
                "role": "preregistered_model_floor",
            }
        )

    checkpoint_steps = (18, 36, 54)
    checkpoint_values = tuple(
        float(
            selection["candidates"][
                f"artifacts/stage2/training/sft-01/checkpoints/checkpoint-{step}"
            ]
        )
        for step in checkpoint_steps
    )
    colors = [COLORS["gray"], COLORS["green"], COLORS["gray"]]
    bars = axes[1].bar(range(3), checkpoint_values, color=colors)
    for bar, value in zip(bars, checkpoint_values, strict=True):
        label_bar(axes[1], bar, value, round(value * 48), 48)
    axes[1].set_title("B. Dev checkpoint selection")
    axes[1].set_xticks(range(3), ["Step 18\nEpoch 1", "Step 36\nEpoch 2", "Step 54\nEpoch 3"])
    axes[1].set_ylim(0, 0.28)
    axes[1].set_yticks(np.arange(0, 0.26, 0.05), [f"{x:.0%}" for x in np.arange(0, 0.26, 0.05)])
    axes[1].set_ylabel("Assigned rule + functional")
    axes[1].grid(axis="y", alpha=0.22)
    axes[1].text(
        0.5,
        0.84,
        "Checkpoint 36 selected\nusing the one-task dev split",
        transform=axes[1].transAxes,
        ha="center",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2.5},
    )
    for step, value in zip(checkpoint_steps, checkpoint_values, strict=True):
        source_rows.append(
            {
                "panel": "dev_selection",
                "metric": f"checkpoint_{step}",
                "numerator": round(value * 48),
                "denominator": 48,
                "rate": value,
                "role": "dev_checkpoint_selection",
            }
        )

    preserved = sum(row["policy_visibility"] == "preserved" for row in audit_rows)
    test_values = (
        float(test_task["functional_rate"]),
        float(test_task["assigned_policy_and_functional_rate"]),
        preserved / len(audit_rows),
    )
    test_counts = ((47, 144), (32, 144), (preserved, len(audit_rows)))
    test_labels = ("Functional\ncode", "Assigned rule\n+ functional", "Policy visible\nin plan")
    bars = axes[2].bar(
        range(3), test_values, color=[COLORS["blue"], COLORS["orange"], COLORS["teal"]]
    )
    for bar, value, counts in zip(bars, test_values, test_counts, strict=True):
        label_bar(axes[2], bar, value, *counts)
    axes[2].set_title("C. Held-out archive task")
    axes[2].set_xticks(range(3), test_labels)
    axes[2].set_ylim(0, 1.05)
    axes[2].set_yticks(np.linspace(0, 1, 6), [f"{x:.0%}" for x in np.linspace(0, 1, 6)])
    axes[2].grid(axis="y", alpha=0.22)
    axes[2].text(
        0.5,
        0.04,
        "One-task case study · no generalization claim",
        transform=axes[2].transAxes,
        ha="center",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2.5},
    )
    for label, value, counts in zip(test_labels, test_values, test_counts, strict=True):
        source_rows.append(
            {
                "panel": "heldout_test",
                "metric": label.replace("\n", " "),
                "numerator": counts[0],
                "denominator": counts[1],
                "rate": value,
                "role": "single_heldout_task_case_study",
            }
        )

    fig.suptitle(
        "Stage 2: base-model floor passed; held-out transfer remained limited",
        fontsize=18,
        fontweight="bold",
    )
    add_note(fig)
    return save_figure(fig, output, "01-key-stage2-evidence"), source_rows


def training_dynamics(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    history = sources["training_result"]["train_log_history"]
    train = [row for row in history if "loss" in row]
    dev = [row for row in history if "eval_loss" in row]
    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    ax.plot(
        [int(row["step"]) for row in train],
        [float(row["loss"]) for row in train],
        color=COLORS["blue"],
        linewidth=1.7,
        marker="o",
        markersize=3,
        label="Training loss",
    )
    ax.set_yscale("log")
    ax.set_xlabel("Optimizer step")
    ax.set_ylabel("Training loss (log scale)", color=COLORS["blue"])
    ax.tick_params(axis="y", labelcolor=COLORS["blue"])
    ax.grid(alpha=0.22, which="both")
    right = ax.twinx()
    right.plot(
        [int(row["step"]) for row in dev],
        [float(row["eval_loss"]) for row in dev],
        color=COLORS["orange"],
        linewidth=2.0,
        marker="D",
        markersize=6,
        label="Dev loss",
    )
    right.set_ylabel("Dev loss", color=COLORS["orange"])
    right.tick_params(axis="y", labelcolor=COLORS["orange"])
    right.set_ylim(2.2, 2.7)
    lines = ax.get_lines() + right.get_lines()
    ax.legend(
        handles=lines,
        labels=[str(line.get_label()) for line in lines],
        loc="center right",
    )
    ax.set_title("QLoRA training dynamics")
    add_note(
        fig,
        "Training used 144 rows for three epochs (54 optimizer steps). Behavioral dev performance, "
        "not loss, selected the checkpoint; the test split was not accessed during training.",
    )
    source_rows = [
        {
            "series": "training_loss" if "loss" in row else "dev_loss",
            "step": int(row["step"]),
            "epoch": float(row["epoch"]),
            "value": float(row.get("loss", row.get("eval_loss"))),
        }
        for row in history
        if "loss" in row or "eval_loss" in row
    ]
    return save_figure(fig, output, "02-training-dynamics"), source_rows


def checkpoint_details(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    reports = (sources["dev_18_final"], sources["dev_36_final"], sources["dev_54_final"])
    steps = (18, 36, 54)
    series = (
        ("Overall", "selection_metric_value", COLORS["green"]),
        ("Structured full", "structured/full", COLORS["blue"]),
        ("Free-form full", "freeform/full", COLORS["orange"]),
    )
    fig, ax = plt.subplots(figsize=(10.5, 6.3))
    x = np.arange(3)
    width = 0.24
    source_rows: list[dict[str, Any]] = []
    for offset, (label, key, color) in zip((-1, 0, 1), series, strict=True):
        if key == "selection_metric_value":
            values = [float(report[key]) for report in reports]
        else:
            values = [
                float(report["by_format_and_concision"][key]["assigned_policy_and_functional_rate"])
                for report in reports
            ]
        bars = ax.bar(x + offset * width, values, width, label=label, color=color)
        for bar, value in zip(bars, values, strict=True):
            label_bar(ax, bar, value, inside=value >= 0.13)
        source_rows.extend(
            {
                "checkpoint_step": step,
                "series": label,
                "assigned_policy_and_functional_rate": value,
                "selected": step == 36,
            }
            for step, value in zip(steps, values, strict=True)
        )
    ax.axvspan(0.55, 1.45, color=COLORS["green"], alpha=0.08)
    ax.set_title("Dev-only behavioral checkpoint comparison")
    ax.set_ylabel("Assigned rule + functional")
    ax.set_xticks(x, ["Step 18\nEpoch 1", "Step 36\nEpoch 2", "Step 54\nEpoch 3"])
    ax.set_ylim(0, 0.34)
    ax.set_yticks(np.arange(0, 0.31, 0.05), [f"{x:.0%}" for x in np.arange(0, 0.31, 0.05)])
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper left")
    add_note(fig, "Dev task: SSRF redirect; 48 full-plan renderer outputs per checkpoint.")
    return save_figure(fig, output, "03-dev-checkpoint-details"), source_rows


def test_condition_performance(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    metrics = sources["test_final"]["by_format_and_concision"]
    functionality = [float(metrics[cell]["functional_rate"]) for cell in FORMAT_CONCISION_ORDER]
    joint = [
        float(metrics[cell]["assigned_policy_and_functional_rate"])
        for cell in FORMAT_CONCISION_ORDER
    ]
    plan_tokens = [float(metrics[cell]["mean_plan_tokens"]) for cell in FORMAT_CONCISION_ORDER]
    fig, ax = plt.subplots(figsize=(12.5, 6.5))
    x = np.arange(len(FORMAT_CONCISION_ORDER))
    width = 0.34
    fbars = ax.bar(x - width / 2, functionality, width, color=COLORS["blue"], label="Functional")
    jbars = ax.bar(
        x + width / 2,
        joint,
        width,
        color=COLORS["green"],
        label="Assigned rule + functional",
    )
    for index in range(len(x)):
        label_bar(ax, fbars[index], functionality[index], inside=functionality[index] >= 0.2)
        label_bar(ax, jbars[index], joint[index], inside=joint[index] >= 0.12)
    ax.set_title("Held-out test performance by plan format and requested length")
    ax.set_ylabel("Rate across 24 renderer outputs per condition")
    ax.set_xticks(x, [CELL_LABELS[cell] for cell in FORMAT_CONCISION_ORDER])
    ax.set_ylim(0, 0.65)
    ax.set_yticks(np.arange(0, 0.61, 0.1), [f"{x:.0%}" for x in np.arange(0, 0.61, 0.1)])
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper right")
    right = ax.twinx()
    right.plot(
        x, plan_tokens, color=COLORS["purple"], marker="D", linewidth=1.7, label="Mean plan tokens"
    )
    right.set_ylabel("Mean exact plan tokens", color=COLORS["purple"])
    right.tick_params(axis="y", labelcolor=COLORS["purple"])
    right.set_ylim(100, 180)
    add_note(
        fig,
        "Held-out task: path_symlink_archive. Exact plan length includes END_PLAN; requested "
        "concision produced little separation in mean length.",
    )
    source_rows = [
        {
            "condition": cell,
            "rows": metrics[cell]["rows"],
            "evaluated_rows": metrics[cell]["evaluated_rows"],
            "functional_rate": metrics[cell]["functional_rate"],
            "assigned_policy_pass_rate_among_functional": metrics[cell][
                "assigned_policy_pass_rate"
            ],
            "assigned_policy_and_functional_rate": metrics[cell][
                "assigned_policy_and_functional_rate"
            ],
            "opposite_policy_and_functional_rate": metrics[cell][
                "opposite_policy_and_functional_rate"
            ],
            "mean_plan_tokens": metrics[cell]["mean_plan_tokens"],
        }
        for cell in FORMAT_CONCISION_ORDER
    ]
    return save_figure(fig, output, "04-heldout-condition-performance"), source_rows


def policy_category(row: dict[str, Any]) -> str:
    if not row["functional"]:
        return "Nonfunctional"
    if row["passes_both_policies"]:
        return "Both"
    if row["assigned_policy_pass"]:
        return "Assigned only"
    if row["opposite_policy_and_functional"]:
        return "Opposite only"
    return "Neither"


def test_outcome_composition(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    rows = sources["test_final"]["rows"]
    categories = ("Assigned only", "Opposite only", "Neither", "Both", "Nonfunctional")
    colors = (
        COLORS["green"],
        COLORS["orange"],
        COLORS["gray"],
        COLORS["purple"],
        COLORS["red"],
    )
    counts: dict[str, Counter[str]] = {}
    for cell in FORMAT_CONCISION_ORDER:
        plan_format, concision = cell.split("/")
        counts[cell] = Counter(
            policy_category(row)
            for row in rows
            if row["plan_format"] == plan_format and row["concision"] == concision
        )
    fig, ax = plt.subplots(figsize=(12.3, 6.4))
    x = np.arange(len(FORMAT_CONCISION_ORDER))
    bottom = np.zeros(len(x))
    for category, color in zip(categories, colors, strict=True):
        values = np.array([counts[cell][category] for cell in FORMAT_CONCISION_ORDER])
        ax.bar(x, values, bottom=bottom, color=color, label=category)
        for index, (value, base) in enumerate(zip(values, bottom, strict=True)):
            if value >= 2:
                ax.text(index, base + value / 2, str(value), ha="center", va="center", fontsize=8)
        bottom += values
    ax.set_title("Held-out functional policy-outcome composition")
    ax.set_ylabel("Renderer outputs (n=24 per condition)")
    ax.set_xticks(x, [CELL_LABELS[cell] for cell in FORMAT_CONCISION_ORDER])
    ax.set_ylim(0, 26)
    ax.set_yticks(range(0, 25, 4))
    ax.grid(axis="y", alpha=0.18)
    ax.legend(loc="upper center", ncol=5)
    add_note(
        fig,
        "Truncated or otherwise nonfunctional attempts remain in the denominator as model "
        "failures; "
        "no functional output passed both mutually exclusive policy suites.",
    )
    source_rows = [
        {"condition": cell, "category": category, "count": counts[cell][category]}
        for cell in FORMAT_CONCISION_ORDER
        for category in categories
    ]
    return save_figure(fig, output, "05-heldout-policy-outcomes"), source_rows


def plan_audit_and_certificates(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    audit_rows = sources["test_plan_audit"]["rows"]
    render_rows = sources["test_final"]["rows"]
    grouped_audit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_render: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audit_rows:
        grouped_audit[f"{row['plan_format']}/{row['concision']}"].append(row)
    for row in render_rows:
        grouped_render[f"{row['plan_format']}/{row['concision']}"].append(row)

    correct_rates: list[float] = []
    visible_rates: list[float] = []
    certificate_rates: list[float] = []
    source_rows: list[dict[str, Any]] = []
    for cell in FORMAT_CONCISION_ORDER:
        plans = grouped_audit[cell]
        renders = grouped_render[cell]
        correct = sum(row["clause_selection"] == "correct" for row in plans)
        visible = sum(row["policy_visibility"] == "preserved" for row in plans)
        certificate_pool = [
            row for row in renders if row["visible_policy_retained"] and row["functional"]
        ]
        false_certificates = sum(not row["assigned_policy_pass"] for row in certificate_pool)
        correct_rates.append(correct / len(plans))
        visible_rates.append(visible / len(plans))
        certificate_rates.append(
            false_certificates / len(certificate_pool) if certificate_pool else np.nan
        )
        source_rows.append(
            {
                "condition": cell,
                "plans": len(plans),
                "correct_clause_selection": correct,
                "policy_visibility_preserved": visible,
                "visible_and_functional_renders": len(certificate_pool),
                "false_certificates": false_certificates,
                "false_certificate_rate": certificate_rates[-1],
            }
        )

    fig, (left, right) = plt.subplots(1, 2, figsize=(14, 6.3), gridspec_kw={"wspace": 0.36})
    x = np.arange(len(FORMAT_CONCISION_ORDER))
    audit_matrix = np.array([correct_rates, visible_rates])
    left.imshow(audit_matrix, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    for row_index, values in enumerate((correct_rates, visible_rates)):
        for column_index, value in enumerate(values):
            left.text(
                column_index,
                row_index,
                f"{round(value * 6)}/6\n{value:.1%}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if value >= 0.72 else COLORS["dark"],
            )
    left.set_title("Behavior-blinded plan audit")
    left.set_yticks([0, 1], ["Correct clause", "Policy preserved"])
    left.set_xticks(x, [CELL_LABELS[cell] for cell in FORMAT_CONCISION_ORDER], fontsize=8)

    bars = right.bar(x, certificate_rates, color=COLORS["purple"])
    for index, (bar, value) in enumerate(zip(bars, certificate_rates, strict=True)):
        row = source_rows[index]
        label_bar(
            right,
            bar,
            value,
            row["false_certificates"],
            row["visible_and_functional_renders"],
            inside=value >= 0.12,
        )
    right.set_title("False certificates among visible, functional outputs")
    right.set_ylabel("Plan states rule, code fails it")
    right.set_xticks(x, [CELL_LABELS[cell] for cell in FORMAT_CONCISION_ORDER], fontsize=8)
    right.set_ylim(0, 0.8)
    right.set_yticks(np.arange(0, 0.81, 0.2), [f"{x:.0%}" for x in np.arange(0, 0.81, 0.2)])
    right.grid(axis="y", alpha=0.22)
    add_note(
        fig,
        "Plan audit n=6 per condition (36 total). False-certificate denominators are the rendered "
        "outputs whose audited plan preserved the policy and whose code was functional.",
    )
    return save_figure(fig, output, "06-plan-audit-and-false-certificates"), source_rows


def bottleneck_sanity(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    values = sources["test_final"]["bottleneck_sanity"]
    metrics = (
        (
            "Functionality",
            float(values["full_document_direct_functional"]),
            float(values["full_structured_plan_functional"]),
            float(values["functional_max_drop"]),
            bool(values["functional_within_tolerance"]),
        ),
        (
            "Assigned rule + functional",
            float(values["full_document_direct_assigned_and_functional"]),
            float(values["full_structured_plan_assigned_and_functional"]),
            float(values["assigned_policy_max_drop"]),
            bool(values["assigned_policy_within_tolerance"]),
        ),
    )
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    x = np.arange(2)
    width = 0.34
    direct = [metric[1] for metric in metrics]
    bottleneck = [metric[2] for metric in metrics]
    dbars = ax.bar(x - width / 2, direct, width, color=COLORS["blue"], label="Full document → code")
    pbars = ax.bar(
        x + width / 2,
        bottleneck,
        width,
        color=COLORS["orange"],
        label="Trained plan → code",
    )
    for bars, rates in ((dbars, direct), (pbars, bottleneck)):
        for bar, rate in zip(bars, rates, strict=True):
            label_bar(ax, bar, rate)
    for index, metric in enumerate(metrics):
        drop = metric[1] - metric[2]
        label = f"drop {drop * 100:.1f} pp\n{'within' if metric[4] else 'outside'} tolerance"
        ax.text(
            index,
            0.08,
            label,
            ha="center",
            fontsize=9,
            color=COLORS["dark"],
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2.5},
        )
    ax.set_title("Held-out planner-to-renderer bottleneck sanity check")
    ax.set_ylabel("Rate")
    ax.set_xticks(x, [metric[0] for metric in metrics])
    ax.set_ylim(0, 0.68)
    ax.set_yticks(np.arange(0, 0.61, 0.1), [f"{x:.0%}" for x in np.arange(0, 0.61, 0.1)])
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="upper right")
    add_note(
        fig,
        "The 8.3-point functionality drop exceeded the 5-point diagnostic tolerance; the "
        "assigned-policy-and-functional rate had no drop and stayed within its 10-point tolerance.",
    )
    source_rows = [
        {
            "metric": metric[0],
            "full_document_direct": metric[1],
            "full_structured_plan": metric[2],
            "drop": metric[1] - metric[2],
            "max_tolerated_drop": metric[3],
            "within_tolerance": metric[4],
        }
        for metric in metrics
    ]
    return save_figure(fig, output, "07-bottleneck-sanity"), source_rows


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
        "# Stage 2 final figures\n\n"
        "These figures summarize the finalized Stage-1-linked Stage 2 pilot artifacts. The local "
        "Qwen3.5-4B model passed the preregistered model-floor check, checkpoint 36 was selected "
        "using the one-task dev split, and final evaluation used the single held-out archive "
        "task.\n\n"
        "## Figures\n\n"
        "1. Key evidence: model floor, dev checkpoint selection, and held-out outcome summary.\n"
        "2. QLoRA training and dev-loss dynamics.\n"
        "3. Detailed behavioral comparison of the three dev checkpoints.\n"
        "4. Held-out functionality, policy behavior, and mean plan length by condition.\n"
        "5. Held-out functional policy-outcome composition.\n"
        "6. Behavior-blinded plan audit and false-certificate rates.\n"
        "7. Full-document versus planner-to-renderer bottleneck sanity check.\n\n"
        "Each figure is emitted as a 300-DPI PNG and editable SVG. CSV files contain the plotted "
        "values, and `figure-manifest.json` records SHA-256 hashes for every source and output.\n\n"
        "The test result is a one-task case study, not evidence of population-level "
        "generalization. A completed attempt that was truncated or otherwise unevaluable remains "
        "a model failure in "
        "unconditional denominators. No functional output passed both policy suites.\n\n"
        "Regenerate from the repository root with:\n\n"
        "```bash\n"
        "uv run --extra plots python scripts/plot_stage2_results.py\n"
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
    builders = (
        ("key-evidence.csv", key_evidence),
        ("training-dynamics.csv", training_dynamics),
        ("dev-checkpoint-details.csv", checkpoint_details),
        ("heldout-condition-performance.csv", test_condition_performance),
        ("heldout-policy-outcomes.csv", test_outcome_composition),
        ("plan-audit-and-false-certificates.csv", plan_audit_and_certificates),
        ("bottleneck-sanity.csv", bottleneck_sanity),
    )
    for csv_name, builder in builders:
        figure_files, rows = builder(sources, output)
        generated.extend(figure_files)
        path = output / csv_name
        write_csv(path, rows)
        generated.append(path)
    generated.append(write_readme(output))

    manifest_path = output / "figure-manifest.json"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "stage2_status": sources["test_final"]["stage2_status"],
        "stage1_gate": sources["test_final"]["stage1_gate"],
        "model_floor_recommendation": sources["model_floor_final"]["model_floor"]["recommendation"],
        "selected_checkpoint_step": sources["checkpoint_selection"]["selected_adapter"][
            "global_step"
        ],
        "pilot": True,
        "base_task_split": {"train": 3, "dev": 1, "test": 1},
        "generalization_claim": "none_single_heldout_task_case_study",
        "sources": [
            {"name": name, "path": path.as_posix(), "sha256": sha256(path.resolve())}
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
