#!/usr/bin/env python3
"""Generate the complete descriptive Stage 0 figure and source-data packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

DEFAULT_REPORT = Path(
    "artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json"
)
DEFAULT_OUTPUT = Path("artifacts/stage0/figures/final")

CONDITIONS = (
    "original_benchmark",
    "surface_only_direct",
    "relevant_clause_only_a",
    "relevant_clause_only_b",
    "full_document_a",
    "full_document_b",
    "native_thinking_full_document_a",
    "native_thinking_full_document_b",
)
CONDITION_LABELS = {
    "original_benchmark": "Original\nbenchmark",
    "surface_only_direct": "Surface\nonly",
    "relevant_clause_only_a": "Relevant\nA",
    "relevant_clause_only_b": "Relevant\nB",
    "full_document_a": "Full doc\nA",
    "full_document_b": "Full doc\nB",
    "native_thinking_full_document_a": "Full + think\nA",
    "native_thinking_full_document_b": "Full + think\nB",
}
AB_CONDITIONS = CONDITIONS[2:]
TASK_ORDER = (
    "path_symlink_report",
    "path_symlink_archive",
    "sql_identifier",
    "command_executable",
    "ssrf_redirect",
)
TASK_LABELS = {
    "path_symlink_report": "Symlink report",
    "path_symlink_archive": "Symlink archive",
    "sql_identifier": "SQL identifier",
    "command_executable": "Command executable",
    "ssrf_redirect": "SSRF redirect",
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
PILOT_NOTE = "Five-task feasibility study; one generation per task-condition cell."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Stage 0 report must be a JSON object")
    if value.get("recommendation") != "continue_to_stage1":
        raise ValueError("figures require the completed continue_to_stage1 Stage 0 report")
    if value.get("scored_jobs") != value.get("expected_jobs") or value.get("scored_jobs") != 40:
        raise ValueError("figures require exactly 40/40 scored Stage 0 jobs")
    observed = {str(row["condition"]) for row in value["outcomes"]}
    if observed != set(CONDITIONS):
        raise ValueError("Stage 0 report condition set is not the frozen eight-condition design")
    return value


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
            "svg.hashsalt": "sable-ir-stage0",
        }
    )


def save_figure(fig: plt.Figure, output: Path, stem: str) -> tuple[Path, Path]:
    fig.tight_layout()
    png = output / f"{stem}.png"
    svg = output / f"{stem}.svg"
    metadata = {"Title": stem, "Author": "sable-ir", "Creation Time": None}
    fig.savefig(png, bbox_inches="tight", facecolor="white", metadata=metadata)
    fig.savefig(
        svg,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Title": stem, "Creator": "sable-ir", "Date": None},
    )
    plt.close(fig)
    return png, svg


def add_pilot_note(fig: plt.Figure, extra: str = "") -> None:
    note = PILOT_NOTE if not extra else f"{PILOT_NOTE} {extra}"
    fig.text(0.01, 0.005, note, ha="left", va="bottom", fontsize=8, color="#555555")


def percentage_label(ax: plt.Axes, bars: Any, values: list[float]) -> None:
    for bar, value in zip(bars, values, strict=True):
        if np.isnan(value):
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.025,
            f"{value:.0%}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def condition_performance(report: dict[str, Any], output: Path) -> list[Path]:
    metrics = report["condition_metrics"]
    functionality = [float(metrics[name]["functional_rate"]) for name in CONDITIONS]
    joint = [
        np.nan
        if metrics[name]["assigned_policy_and_functional_rate"] is None
        else float(metrics[name]["assigned_policy_and_functional_rate"])
        for name in CONDITIONS
    ]
    x = np.arange(len(CONDITIONS))
    width = 0.36
    fig, ax = plt.subplots(figsize=(13.5, 6.5))
    functional_bars = ax.bar(
        x - width / 2, functionality, width, label="Functional", color=COLORS["blue"]
    )
    joint_bars = ax.bar(
        x + width / 2,
        joint,
        width,
        label="Assigned policy + functional",
        color=COLORS["green"],
    )
    percentage_label(ax, functional_bars, functionality)
    percentage_label(ax, joint_bars, joint)
    ax.set_title("Stage 0 performance by prompt condition")
    ax.set_ylabel("Proportion of outputs")
    ax.set_xticks(x, [CONDITION_LABELS[name] for name in CONDITIONS])
    ax.set_ylim(0, 1.14)
    ax.set_yticks(np.linspace(0, 1, 6), [f"{value:.0%}" for value in np.linspace(0, 1, 6)])
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", ncol=2)
    ax.text(
        0.99,
        0.98,
        "A/B policy metrics are not applicable to the benchmark anchor or surface-only condition.",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color="#555555",
    )
    add_pilot_note(fig, "Each bar is based on five outputs.")
    return list(save_figure(fig, output, "01-condition-performance"))


def information_level_comparison(report: dict[str, Any], output: Path) -> list[Path]:
    metrics = report["condition_metrics"]
    derived = report["derived"]
    labels = ("Surface only", "Relevant clause", "Full document", "Full + thinking")
    functionality = [
        float(metrics["surface_only_direct"]["functional_rate"]),
        float(derived["relevant_functional_rate"]),
        float(derived["full_functional_rate"]),
        (
            float(metrics["native_thinking_full_document_a"]["functional_rate"])
            + float(metrics["native_thinking_full_document_b"]["functional_rate"])
        )
        / 2,
    ]
    policy = [
        float(derived["surface_balanced_policy_given_functional_rate"]),
        float(derived["relevant_assigned_policy_given_functional_rate"]),
        float(derived["full_assigned_policy_given_functional_rate"]),
        float(derived["native_thinking_assigned_policy_given_functional_rate"]),
    ]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    fbars = ax.bar(x - width / 2, functionality, width, color=COLORS["blue"], label="Functional")
    pbars = ax.bar(
        x + width / 2,
        policy,
        width,
        color=COLORS["green"],
        label="Policy metric among functional outputs",
    )
    percentage_label(ax, fbars, functionality)
    percentage_label(ax, pbars, policy)
    ax.set_title("Functionality and policy behavior by information level")
    ax.set_ylabel("Proportion")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.14)
    ax.set_yticks(np.linspace(0, 1, 6), [f"{value:.0%}" for value in np.linspace(0, 1, 6)])
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left")
    add_pilot_note(
        fig,
        "Surface n=5; each A/B information level n=10. Surface policy bar is the balanced "
        "A/B-suite baseline; the others use assigned-rule compliance.",
    )
    return list(save_figure(fig, output, "02-information-level-comparison"))


def outcome_lookup(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["task_id"]), str(row["condition"])): row for row in report["outcomes"]}


def exact_pair_success(rows: dict[tuple[str, str], dict[str, Any]], task: str, prefix: str) -> bool:
    a = rows[(task, f"{prefix}_a")]
    b = rows[(task, f"{prefix}_b")]
    return bool(
        a["functionality"] == "pass"
        and b["functionality"] == "pass"
        and a["policy_a"] == "pass"
        and a["policy_b"] == "fail"
        and b["policy_a"] == "fail"
        and b["policy_b"] == "pass"
    )


def paired_controllability(
    report: dict[str, Any], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    rows = outcome_lookup(report)
    modes = (
        ("Relevant clause", "relevant_clause_only"),
        ("Full document", "full_document"),
        ("Full + thinking", "native_thinking_full_document"),
    )
    matrix = np.array(
        [
            [1 if exact_pair_success(rows, task, prefix) else 0 for _label, prefix in modes]
            for task in TASK_ORDER
        ]
    )
    aggregate = matrix.mean(axis=0)
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(13, 6.3), gridspec_kw={"width_ratios": [1.45, 1]}
    )
    cmap = ListedColormap(["#F3C6C6", "#B9DFB4"])
    left.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    left.set_title("Exact A-only → B-only switch by task")
    left.set_xticks(range(len(modes)), [label for label, _prefix in modes])
    left.set_yticks(range(len(TASK_ORDER)), [TASK_LABELS[task] for task in TASK_ORDER])
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            left.text(
                col_index,
                row_index,
                "✓" if matrix[row_index, col_index] else "×",
                ha="center",
                va="center",
                fontsize=18,
                color=COLORS["dark"],
            )
    bars = right.bar(
        np.arange(len(modes)), aggregate, color=[COLORS["blue"], COLORS["teal"], COLORS["purple"]]
    )
    right.hlines(
        0.20,
        0.65,
        1.35,
        color=COLORS["red"],
        linestyle="--",
        linewidth=1.5,
        label="G5 gate (full document only)",
    )
    percentage_label(right, bars, list(aggregate))
    right.set_title("Controllability across all five task pairs")
    right.set_ylabel("Successful pairs")
    right.set_xticks(np.arange(len(modes)), [label for label, _prefix in modes], rotation=15)
    right.set_ylim(0, 1.14)
    right.set_yticks(np.linspace(0, 1, 6), [f"{value:.0%}" for value in np.linspace(0, 1, 6)])
    right.grid(axis="y", alpha=0.25)
    right.legend(loc="upper left")
    add_pilot_note(
        fig, "Nonfunctional pairs count as failed switches; denominator is five per mode."
    )
    source_rows = [
        {
            "task_id": task,
            "information_condition": label,
            "exact_a_only_to_b_only_switch": int(matrix[row_index, col_index]),
        }
        for row_index, task in enumerate(TASK_ORDER)
        for col_index, (label, _prefix) in enumerate(modes)
    ]
    return list(save_figure(fig, output, "03-paired-policy-controllability")), source_rows


def policy_category(row: dict[str, Any]) -> str:
    if row["functionality"] != "pass":
        return "Nonfunctional"
    a = row["policy_a"] == "pass"
    b = row["policy_b"] == "pass"
    if a and b:
        return "Both"
    if a:
        return "A only"
    if b:
        return "B only"
    return "Neither"


def policy_outcome_composition(
    report: dict[str, Any], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    categories = ("A only", "B only", "Neither", "Both", "Nonfunctional")
    color_order = (
        COLORS["orange"],
        COLORS["teal"],
        COLORS["gray"],
        COLORS["purple"],
        COLORS["red"],
    )
    report_rows = report["outcomes"]
    counts = {
        condition: {
            category: sum(
                policy_category(row) == category
                for row in report_rows
                if row["condition"] == condition
            )
            for category in categories
        }
        for condition in AB_CONDITIONS
    }
    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(AB_CONDITIONS))
    bottom = np.zeros(len(AB_CONDITIONS))
    for category, color in zip(categories, color_order, strict=True):
        values = np.array([counts[name][category] for name in AB_CONDITIONS])
        ax.bar(x, values, bottom=bottom, color=color, label=category)
        for index, (value, base) in enumerate(zip(values, bottom, strict=True)):
            if value:
                ax.text(index, base + value / 2, str(value), ha="center", va="center", fontsize=9)
        bottom += values
    ax.set_title("Functional policy-outcome composition")
    ax.set_ylabel("Outputs (n=5 per condition)")
    ax.set_xticks(x, [CONDITION_LABELS[name] for name in AB_CONDITIONS])
    ax.set_ylim(0, 5.55)
    ax.set_yticks(range(0, 6))
    ax.legend(loc="upper center", ncol=5)
    ax.grid(axis="y", alpha=0.18)
    add_pilot_note(fig, "Policy category is assigned only after ordinary functionality passes.")
    source_rows = [
        {"condition": condition, "category": category, "count": counts[condition][category]}
        for condition in AB_CONDITIONS
        for category in categories
    ]
    return list(save_figure(fig, output, "04-policy-outcome-composition")), source_rows


def annotate_binary_heatmap(
    ax: plt.Axes,
    matrix: np.ndarray,
    xlabels: list[str],
    title: str,
) -> None:
    cmap = ListedColormap(["#F3C6C6", "#B9DFB4"])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_title(title)
    ax.set_xticks(range(len(xlabels)), xlabels, rotation=38, ha="right")
    ax.set_yticks(range(len(TASK_ORDER)), [TASK_LABELS[task] for task in TASK_ORDER])
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            ax.text(
                col_index,
                row_index,
                "✓" if matrix[row_index, col_index] else "×",
                ha="center",
                va="center",
                fontsize=13,
                color=COLORS["dark"],
            )


def task_heatmaps(report: dict[str, Any], output: Path) -> list[Path]:
    rows = outcome_lookup(report)
    functional = np.array(
        [
            [
                1 if rows[(task, condition)]["functionality"] == "pass" else 0
                for condition in CONDITIONS
            ]
            for task in TASK_ORDER
        ]
    )
    assigned_joint = np.array(
        [
            [
                1
                if rows[(task, condition)]["functionality"] == "pass"
                and rows[(task, condition)]["policy_a" if condition.endswith("_a") else "policy_b"]
                == "pass"
                else 0
                for condition in AB_CONDITIONS
            ]
            for task in TASK_ORDER
        ]
    )
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 9.2), gridspec_kw={"hspace": 0.65})
    annotate_binary_heatmap(
        axes[0],
        functional,
        [CONDITION_LABELS[name].replace("\n", " ") for name in CONDITIONS],
        "Ordinary functionality by task and condition",
    )
    annotate_binary_heatmap(
        axes[1],
        assigned_joint,
        [CONDITION_LABELS[name].replace("\n", " ") for name in AB_CONDITIONS],
        "Assigned-policy-and-functional success by task and A/B condition",
    )
    fig.legend(
        handles=[
            Patch(facecolor="#B9DFB4", label="Pass"),
            Patch(facecolor="#F3C6C6", label="Fail"),
        ],
        loc="upper center",
        ncol=2,
    )
    add_pilot_note(fig, "Each square is one generation; no inferential uncertainty is implied.")
    return list(save_figure(fig, output, "05-task-outcome-heatmaps"))


def gate_summary(report: dict[str, Any], output: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    by_id = {gate["gate_id"]: gate for gate in report["gates"]}
    for gate_id in ("G1", "G1b", "G2", "G3", "G4", "G5", "G6", "G7", "G8"):
        if by_id[gate_id]["status"] != "passed":
            raise ValueError(f"cannot plot final pass packet: {gate_id} did not pass")

    def observed(gate_id: str) -> float:
        return float(by_id[gate_id]["observed"])

    table_rows = [
        ("G1", "Relevant-clause-only functionality", "≥ 40%", f"{observed('G1'):.1%}"),
        ("G1b", "Full-document functionality", "≥ 40%", f"{observed('G1b'):.1%}"),
        (
            "G2",
            "Relevant-clause assigned-policy compliance among functional outputs",
            "≥ 50%",
            f"{observed('G2'):.1%}",
        ),
        (
            "G3",
            "Full-document compliance drop relative to relevant-clause-only",
            "≤ 20 points",
            f"{observed('G3') * 100:.1f} points",
        ),
        (
            "G4",
            "Full-document compliance gain over the balanced surface baseline",
            "≥ 20 points",
            f"{observed('G4') * 100:.1f} points",
        ),
        (
            "G5",
            "Jointly functional exact A-only → B-only full-document switching",
            "≥ 20%",
            f"{observed('G5'):.1%}",
        ),
        ("G6", "Functional outputs passing both policy suites", "0 violations", "0 violations"),
        (
            "G7",
            "One applicable clause per document and genuinely irrelevant distractors",
            "Manual audit passes",
            "Audit passed",
        ),
        (
            "G8",
            "Original benchmark outputs that are secure and functional",
            "≥ 20%",
            f"{observed('G8'):.1%}",
        ),
    ]
    headers = ("Gate", "What it checks", "Pass rule", "Observed result", "Status")
    cell_text = [
        [gate_id, textwrap.fill(description, 48), rule, result, "PASSED"]
        for gate_id, description, rule, result in table_rows
    ]
    fig, ax = plt.subplots(figsize=(14.5, 8.7))
    ax.axis("off")
    fig.suptitle("Stage 0 continuation-gate summary", y=0.96, fontsize=20, fontweight="bold")
    fig.text(
        0.5,
        0.905,
        "All eight automatic gates and the manual document-integrity audit passed.",
        ha="center",
        fontsize=11,
        color="#555555",
    )
    table = ax.table(
        cellText=cell_text,
        colLabels=headers,
        cellLoc="left",
        colLoc="left",
        colWidths=[0.07, 0.46, 0.16, 0.16, 0.15],
        bbox=[0.0, 0.08, 1.0, 0.78],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("white")
        cell.set_linewidth(1.5)
        if row == 0:
            cell.set_facecolor(COLORS["dark"])
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#F3F5F7" if row % 2 else "#E8EDF1")
            if column == 0:
                cell.get_text().set_fontweight("bold")
            if column == 4:
                cell.set_facecolor("#B9DFB4")
                cell.get_text().set_color("#245225")
                cell.get_text().set_fontweight("bold")
    add_pilot_note(
        fig, "Gate thresholds are engineering continuation rules, not significance tests."
    )
    source_rows = [
        {
            "gate_id": gate_id,
            "description": description,
            "observed": result,
            "threshold": rule,
            "rule": "manual" if gate_id == "G7" else "numeric",
            "status": by_id[gate_id]["status"],
        }
        for gate_id, description, rule, result in table_rows
    ]
    return list(save_figure(fig, output, "06-gate-summary")), source_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def condition_source_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"condition": condition, **report["condition_metrics"][condition]}
        for condition in CONDITIONS
    ]


def outcome_source_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            key: row[key]
            for key in (
                "job_id",
                "task_id",
                "condition",
                "assigned_policy",
                "compilation",
                "functionality",
                "policy_a",
                "policy_b",
                "original_security",
            )
        }
        for row in report["outcomes"]
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_readme(output: Path, report_path: Path) -> Path:
    readme = output / "README.md"
    readme.write_text(
        "# Stage 0 final figures\n\n"
        f"Source: `{report_path.as_posix()}`.\n\n"
        "All charts are descriptive summaries of the final corrected-document Stage 0 run. "
        "There are five tasks and one output per task-condition cell; no error bars or "
        "population-level uncertainty claims are shown. The original benchmark is a separate "
        "anchor and is not part of the A/B comparison.\n\n"
        "## Figures\n\n"
        "1. Condition-level functionality and assigned-policy-and-functional performance.\n"
        "2. Functionality and conditional policy behavior by information level.\n"
        "3. Exact paired A-only to B-only controllability by task and condition.\n"
        "4. Functional A-only/B-only/neither/both outcome composition.\n"
        "5. Per-task functionality and assigned-policy heatmaps.\n"
        "6. Automatic continuation-gate summary, with manual G7 noted separately.\n\n"
        "Each figure is emitted as a 300-DPI PNG and an editable SVG. CSV files contain the "
        "plotted source values. `figure-manifest.json` binds every output to the source report.\n\n"
        "Regenerate from the repository root with:\n\n"
        "```bash\n"
        "uv run --extra plots python scripts/plot_stage0_results.py\n"
        "```\n",
        encoding="utf-8",
    )
    return readme


def main() -> None:
    args = parse_args()
    report_path = args.report.resolve()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    report = load_report(report_path)

    generated: list[Path] = []
    generated.extend(condition_performance(report, output))
    generated.extend(information_level_comparison(report, output))
    paired_files, paired_rows = paired_controllability(report, output)
    generated.extend(paired_files)
    composition_files, composition_rows = policy_outcome_composition(report, output)
    generated.extend(composition_files)
    generated.extend(task_heatmaps(report, output))
    gate_files, gate_rows = gate_summary(report, output)
    generated.extend(gate_files)

    csv_payloads = {
        "condition-metrics.csv": condition_source_rows(report),
        "task-outcomes.csv": outcome_source_rows(report),
        "paired-controllability.csv": paired_rows,
        "policy-outcome-composition.csv": composition_rows,
        "gates.csv": gate_rows,
    }
    for name, rows in csv_payloads.items():
        path = output / name
        write_csv(path, rows)
        generated.append(path)
    readme = write_readme(output, args.report)
    generated.append(readme)

    manifest_path = output / "figure-manifest.json"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_report_path": args.report.as_posix(),
        "source_report_sha256": sha256(report_path),
        "source_run_id": report["run_id"],
        "source_recommendation": report["recommendation"],
        "descriptive_pilot": True,
        "independent_task_clusters": 5,
        "samples_per_task_condition": 1,
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
