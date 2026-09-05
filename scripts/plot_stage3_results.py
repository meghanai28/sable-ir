#!/usr/bin/env python3
"""Generate the descriptive Stage 3 figure and source-data packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

DEFAULT_ROOT = Path("artifacts/stage3")
DEFAULT_OUTPUT = DEFAULT_ROOT / "figures/final"
SOURCE_PATHS = {
    "activation_manifest": DEFAULT_ROOT / "activations/act-01/manifest.json",
    "primary_plan_audit": DEFAULT_ROOT / "activations/act-01/plan-audit.json",
    "double_plan_audit": DEFAULT_ROOT / "activations/act-01/plan-audit.double.json",
    "activation_dataset": DEFAULT_ROOT / "activations/act-01/dataset.json",
    "probe_fit": DEFAULT_ROOT / "analysis/fit-01/probes-dev.json",
    "selection": DEFAULT_ROOT / "analysis/fit-01/selection.json",
    "heldout": DEFAULT_ROOT / "analysis/fit-01/heldout.json",
    "report": DEFAULT_ROOT / "analysis/fit-01/report.json",
}

STATE_ORDER = ("planner_input", "planner_output", "renderer_ingestion")
STATE_LABELS = {
    "planner_input": "Planner\ninput",
    "planner_output": "Planner\noutput",
    "renderer_ingestion": "Renderer\ningestion",
}
QUADRANT_ORDER = (
    "faithful_success",
    "false_certificate",
    "hidden_use",
    "visible_omission_behavioral_failure",
)
QUADRANT_LABELS = {
    "faithful_success": "Faithful success",
    "false_certificate": "False certificate",
    "hidden_use": "Hidden use",
    "visible_omission_behavioral_failure": "Visible/omitted\nbehavioral failure",
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
    "Five-task mechanistic pilot with a 3/1/1 task split. Held-out estimates come from one "
    "archive task, so no population-level generalization is claimed and task-clustered "
    "confidence intervals are unavailable."
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
    manifest = sources["activation_manifest"]
    dataset = sources["activation_dataset"]
    probe_fit = sources["probe_fit"]
    selection = sources["selection"]
    heldout = sources["heldout"]
    report = sources["report"]

    if dataset.get("complete") is not True or len(dataset.get("rows", [])) != 240:
        raise ValueError("Stage 3 activation dataset is not the complete 240-plan dataset")
    if dataset.get("malformed_plans") != 0 or dataset.get("unlabeled_rows") != 0:
        raise ValueError("Stage 3 activation dataset contains malformed or unlabeled plans")
    if dataset.get("activation_manifest_sha256") != sha256(SOURCE_PATHS["activation_manifest"]):
        raise ValueError("activation dataset does not bind the activation manifest")
    if dataset.get("primary_audit_sha256") != sha256(SOURCE_PATHS["primary_plan_audit"]):
        raise ValueError("activation dataset does not bind the primary plan audit")
    if dataset.get("double_audit_sha256") != sha256(SOURCE_PATHS["double_plan_audit"]):
        raise ValueError("activation dataset does not bind the double plan audit")
    if selection.get("dataset_sha256") != sha256(SOURCE_PATHS["activation_dataset"]):
        raise ValueError("probe selection does not bind the activation dataset")
    if selection.get("probe_fit_sha256") != sha256(SOURCE_PATHS["probe_fit"]):
        raise ValueError("probe selection does not bind the dev probe fit")
    if heldout.get("dataset_sha256") != sha256(SOURCE_PATHS["activation_dataset"]):
        raise ValueError("held-out analysis does not bind the activation dataset")
    if heldout.get("selection_sha256") != sha256(SOURCE_PATHS["selection"]):
        raise ValueError("held-out analysis does not bind the frozen selection")
    if report.get("dataset_sha256") != sha256(SOURCE_PATHS["activation_dataset"]):
        raise ValueError("Stage 3 report does not bind the activation dataset")
    if report.get("selection_sha256") != sha256(SOURCE_PATHS["selection"]):
        raise ValueError("Stage 3 report does not bind the frozen selection")
    if report.get("heldout_sha256") != sha256(SOURCE_PATHS["heldout"]):
        raise ValueError("Stage 3 report does not bind the held-out analysis")

    status = report.get("status", {})
    if status != {
        "stage1_gate": "passed",
        "stage2_status": "valid_continuation",
        "stage3_status": "valid_continuation",
    }:
        raise ValueError("unexpected Stage 3 lineage status")
    if report.get("causal_evaluation_authorized") is not False:
        raise ValueError("canonical Stage 3 report no longer blocks causal evaluation")
    requirements = report.get("stage4_authorization_requirements", {})
    if requirements != {
        "renderer_ingestion_decodable": False,
        "renderer_ingestion_transfers_to_paraphrase_set2": False,
        "renderer_ingestion_task_directions_align": False,
        "dataset_complete": True,
    }:
        raise ValueError("unexpected Stage 4 authorization results")

    if probe_fit.get("probe_training_unit") != "activation_row":
        raise ValueError("probe fitting no longer uses all activation rows")
    if probe_fit.get("probe_task_weighting") != "equal_total_weight_per_base_task_policy":
        raise ValueError("probe weighting metadata is not task-policy balanced")
    if probe_fit.get("direction_estimation_unit") != "task_level_ab_difference_only":
        raise ValueError("direction estimation no longer uses task-level A/B differences")
    if manifest.get("renderer_adapter_enabled") is not False:
        raise ValueError("renderer adapter was enabled during Stage 3 capture")
    if len(manifest.get("plan_jobs", [])) != 240:
        raise ValueError("activation manifest does not contain 240 plan jobs")
    if len(manifest.get("render_jobs", [])) != 720:
        raise ValueError("activation manifest does not contain 720 render jobs")
    if len(manifest.get("surface_only_jobs", [])) != 10:
        raise ValueError("activation manifest does not contain 10 surface controls")

    state_results = {row["state"]: row for row in heldout.get("states", [])}
    if tuple(state_results) != STATE_ORDER:
        raise ValueError("held-out activation states changed")
    if any(state_results[state].get("decodable") is not False for state in STATE_ORDER):
        raise ValueError("a held-out state unexpectedly became decodable")
    if any(state_results[state].get("transfers_to_set2") is not False for state in STATE_ORDER):
        raise ValueError("a held-out state unexpectedly transferred to set 2")
    if any(selection["direction_layer"].get(state) is not None for state in STATE_ORDER):
        raise ValueError("a shared policy-orientation direction was unexpectedly selected")
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
            "svg.hashsalt": "sable-ir-stage3",
        }
    )


def save_figure(fig: Figure, output: Path, stem: str, *, top: float = 0.96) -> list[Path]:
    fig.tight_layout(rect=(0, 0.06, 1, top))
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


def add_value(ax: Axes, bar: Any, value: float, *, digits: int = 1) -> None:
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.02,
        f"{value:.{digits}%}",
        ha="center",
        va="bottom",
        fontsize=8.5,
    )


def state_map(sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["state"]: row for row in sources["heldout"]["states"]}


def key_evidence(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    states = state_map(sources)
    report = sources["report"]
    primary = report["primary_renderer_ingestion_analysis"]
    fig, axes = plt.subplots(1, 3, figsize=(15.8, 5.8), gridspec_kw={"wspace": 0.38})
    source_rows: list[dict[str, Any]] = []

    x = np.arange(3)
    width = 0.34
    pooled = [float(states[state]["test"]["auroc"]) for state in STATE_ORDER]
    set2 = [float(states[state]["test_set2"]["auroc"]) for state in STATE_ORDER]
    pooled_bars = axes[0].bar(
        x - width / 2, pooled, width, color=COLORS["blue"], label="Pooled held-out"
    )
    set2_bars = axes[0].bar(
        x + width / 2, set2, width, color=COLORS["orange"], label="Paraphrase set 2"
    )
    axes[0].axhline(0.75, color=COLORS["red"], linestyle="--", label="Decoding gate: 0.75")
    axes[0].axhline(0.5, color=COLORS["gray"], linestyle=":", label="Chance: 0.50")
    for bars, values in ((pooled_bars, pooled), (set2_bars, set2)):
        for bar, value in zip(bars, values, strict=True):
            add_value(axes[0], bar, value)
    axes[0].set_title("A. Boundary decoding")
    axes[0].set_xticks(x, [STATE_LABELS[state] for state in STATE_ORDER])
    axes[0].set_ylabel("Held-out AUROC")
    axes[0].set_ylim(0, 1.04)
    axes[0].grid(axis="y", alpha=0.2)
    axes[0].legend(loc="upper left", fontsize=7.7)
    axes[0].text(
        0.5,
        0.04,
        "Pooled scores are localization diagnostics",
        transform=axes[0].transAxes,
        ha="center",
        fontsize=7.8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 2},
    )
    for state, pooled_value, set2_value in zip(STATE_ORDER, pooled, set2, strict=True):
        source_rows.extend(
            [
                {
                    "panel": "boundary_decoding",
                    "condition": state,
                    "metric": "pooled_heldout_auroc",
                    "value": pooled_value,
                    "role": "localization_diagnostic",
                },
                {
                    "panel": "boundary_decoding",
                    "condition": state,
                    "metric": "paraphrase_set2_auroc",
                    "value": set2_value,
                    "role": "transfer_requirement",
                },
            ]
        )

    subset_names = ("omitted_or_blurred", "false_certificate")
    subset_labels = ("Omitted/blurred\n(n=23)", "False certificate\n(n=18)")
    activation = [float(primary[name]["renderer_ingestion"]["auroc"]) for name in subset_names]
    text = [float(primary[name]["best_text"]["auroc"]) for name in subset_names]
    x2 = np.arange(2)
    activation_bars = axes[1].bar(
        x2 - width / 2,
        activation,
        width,
        color=COLORS["purple"],
        label="Renderer activation",
    )
    text_bars = axes[1].bar(
        x2 + width / 2, text, width, color=COLORS["teal"], label="Best text control"
    )
    axes[1].axhline(0.5, color=COLORS["gray"], linestyle=":", label="Chance: 0.50")
    for bars, values in ((activation_bars, activation), (text_bars, text)):
        for bar, value in zip(bars, values, strict=True):
            add_value(axes[1], bar, value)
    axes[1].set_title("B. Primary renderer analysis")
    axes[1].set_xticks(x2, subset_labels)
    axes[1].set_ylabel("Held-out AUROC")
    axes[1].set_ylim(0, 1.04)
    axes[1].grid(axis="y", alpha=0.2)
    axes[1].legend(loc="upper left", fontsize=7.7)
    axes[1].text(
        0.5,
        0.04,
        "Hidden use: insufficient support (6 < 10 rows)",
        transform=axes[1].transAxes,
        ha="center",
        fontsize=7.8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 2},
    )
    for name, activation_value, text_value in zip(subset_names, activation, text, strict=True):
        source_rows.extend(
            [
                {
                    "panel": "primary_renderer_analysis",
                    "condition": name,
                    "metric": "renderer_ingestion_auroc",
                    "value": activation_value,
                    "role": "primary_activation_result",
                },
                {
                    "panel": "primary_renderer_analysis",
                    "condition": name,
                    "metric": "best_text_auroc",
                    "value": text_value,
                    "role": "text_control",
                },
            ]
        )

    requirements = report["stage4_authorization_requirements"]
    checklist = (
        ("Dataset complete", requirements["dataset_complete"]),
        ("Renderer-ingestion\ndecodable", requirements["renderer_ingestion_decodable"]),
        (
            "Transfers to\nparaphrase set 2",
            requirements["renderer_ingestion_transfers_to_paraphrase_set2"],
        ),
        (
            "Task directions\nalign",
            requirements["renderer_ingestion_task_directions_align"],
        ),
    )
    axes[2].set_xlim(0, 1)
    axes[2].set_ylim(-0.75, len(checklist) - 0.25)
    axes[2].set_title("C. Stage 4 authorization")
    axes[2].axis("off")
    for index, (label, passed) in enumerate(reversed(checklist)):
        color = COLORS["green"] if passed else COLORS["red"]
        axes[2].barh(index, 0.93, left=0.035, height=0.68, color=color, alpha=0.16)
        axes[2].text(
            0.09, index, "PASS" if passed else "FAIL", color=color, va="center", fontweight="bold"
        )
        axes[2].text(0.32, index, label, va="center", fontsize=9)
        source_rows.append(
            {
                "panel": "stage4_authorization",
                "condition": label.replace("\n", " "),
                "metric": "passed",
                "value": passed,
                "role": "authorization_requirement",
            }
        )
    axes[2].text(
        0.5,
        -0.58,
        "STAGE 4 NOT AUTHORIZED",
        color=COLORS["red"],
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        bbox={"facecolor": "#FDECEC", "edgecolor": COLORS["red"], "pad": 7},
    )

    fig.suptitle(
        "Stage 3: held-out activations did not support a transferable policy direction",
        fontsize=17,
        fontweight="bold",
    )
    add_note(fig)
    return save_figure(fig, output, "01-key-stage3-evidence"), source_rows


def probe_transfer(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    states = state_map(sources)
    series = (
        ("Pooled", "test", COLORS["blue"]),
        ("Paraphrase set 1", "test_set1", COLORS["teal"]),
        ("Paraphrase set 2", "test_set2", COLORS["orange"]),
    )
    fig, ax = plt.subplots(figsize=(11.2, 6.4))
    x = np.arange(3)
    width = 0.23
    source_rows: list[dict[str, Any]] = []
    for offset, (label, key, color) in zip((-1, 0, 1), series, strict=True):
        values = [float(states[state][key]["auroc"]) for state in STATE_ORDER]
        bars = ax.bar(x + offset * width, values, width, color=color, label=label)
        for bar, value in zip(bars, values, strict=True):
            add_value(ax, bar, value)
        source_rows.extend(
            {
                "state": state,
                "selected_layer": states[state]["probe_layer"],
                "subset": label,
                "rows": states[state][key]["rows"],
                "auroc": value,
            }
            for state, value in zip(STATE_ORDER, values, strict=True)
        )
    ax.axhline(0.75, color=COLORS["red"], linestyle="--", label="Decoding gate: 0.75")
    ax.axhline(0.5, color=COLORS["gray"], linestyle=":", label="Chance: 0.50")
    ax.set_title("Held-out probe performance and paraphrase transfer")
    ax.set_ylabel("AUROC")
    ax.set_xticks(
        x,
        [
            f"{STATE_LABELS[state]}\nselected L{states[state]['probe_layer']}"
            for state in STATE_ORDER
        ],
    )
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="upper center", ncol=3, fontsize=8)
    add_note(
        fig,
        "Each held-out boundary contains 48 rows (24 per paraphrase set). No boundary met "
        "the decoding threshold and transferred to disjoint paraphrase set 2.",
    )
    return save_figure(fig, output, "02-heldout-probe-transfer"), source_rows


def renderer_controls(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    renderer = state_map(sources)["renderer_ingestion"]
    baselines = renderer["baselines_test"]
    rows = [
        ("Renderer activation", float(renderer["test"]["auroc"]), "activation"),
        ("TF-IDF", float(baselines["tfidf"]["auroc"]), "text"),
        ("Plan length", float(baselines["plan_length"]["auroc"]), "text"),
        ("TF-IDF + length", float(baselines["tfidf_plus_length"]["auroc"]), "text"),
        (
            "Clause length + position",
            float(baselines["clause_length_and_position"]["auroc"]),
            "metadata",
        ),
        ("Shuffled labels", float(renderer["shuffled_labels_test"]["auroc"]), "negative"),
        ("Surface-only labels", float(renderer["surface_only_control"]["auroc"]), "negative"),
    ]
    rows.sort(key=lambda row: row[1])
    colors = {
        "activation": COLORS["purple"],
        "text": COLORS["teal"],
        "metadata": COLORS["orange"],
        "negative": COLORS["gray"],
    }
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    bars = ax.barh(
        np.arange(len(rows)),
        [value for _, value, _ in rows],
        color=[colors[role] for _, _, role in rows],
    )
    ax.axvline(0.75, color=COLORS["red"], linestyle="--", label="Decoding gate: 0.75")
    ax.axvline(0.5, color=COLORS["gray"], linestyle=":", label="Chance: 0.50")
    for bar, (_, value, _) in zip(bars, rows, strict=True):
        ax.text(value + 0.012, bar.get_y() + bar.get_height() / 2, f"{value:.1%}", va="center")
    ax.set_title("Renderer-ingestion activation and non-activation controls")
    ax.set_xlabel("Held-out AUROC")
    ax.set_yticks(np.arange(len(rows)), [label for label, _, _ in rows])
    ax.set_xlim(0, 1.02)
    ax.grid(axis="x", alpha=0.2)
    ax.legend(loc="lower right")
    add_note(
        fig,
        "The best text/metadata control reached 81.2% AUROC, while the renderer-ingestion "
        "activation probe reached 57.8%; balanced counterfactual surface labels are a negative "
        "control, not genuine policy inputs.",
    )
    source_rows = [
        {"condition": label, "auroc": value, "role": role} for label, value, role in rows
    ]
    return save_figure(fig, output, "03-renderer-controls"), source_rows


def dev_layer_sweep(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    selected = sources["selection"]["probe_layer"]
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.7), sharey=True)
    source_rows: list[dict[str, Any]] = []
    for ax, state_row in zip(axes, sources["probe_fit"]["states"], strict=True):
        state = state_row["state"]
        cells = state_row["cells"]
        layers = [int(cell["layer"]) for cell in cells]
        for label, key, color in (
            ("Pooled dev", "dev", COLORS["blue"]),
            ("Dev set 1", "dev_set1", COLORS["teal"]),
            ("Dev set 2", "dev_set2", COLORS["orange"]),
        ):
            values = [float(cell[key]["auroc"]) for cell in cells]
            ax.plot(
                layers, values, marker="o", markersize=3.5, linewidth=1.4, color=color, label=label
            )
            source_rows.extend(
                {
                    "state": state,
                    "layer": layer,
                    "subset": label,
                    "auroc": value,
                    "selected_layer": layer == selected[state],
                }
                for layer, value in zip(layers, values, strict=True)
            )
        ax.axhline(0.75, color=COLORS["red"], linestyle="--", linewidth=1.2)
        ax.axvline(selected[state], color=COLORS["dark"], linestyle=":", linewidth=1.4)
        ax.scatter(
            [selected[state]],
            [
                next(
                    float(cell["dev"]["auroc"])
                    for cell in cells
                    if cell["layer"] == selected[state]
                )
            ],
            s=70,
            facecolors="none",
            edgecolors=COLORS["dark"],
            linewidths=1.8,
            zorder=4,
        )
        ax.set_title(STATE_LABELS[state].replace("\n", " "))
        ax.set_xlabel("Layer")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.18)
        ax.text(
            0.5,
            0.04,
            f"Frozen selection: L{selected[state]}",
            transform=ax.transAxes,
            ha="center",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
        )
    axes[0].set_ylabel("Dev AUROC")
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Dev-only layer selection diagnostics", fontsize=17, fontweight="bold")
    add_note(
        fig,
        "Layers and regularization were frozen on the one-task dev split before held-out "
        "evaluation. High dev scores are selection diagnostics, not held-out evidence.",
    )
    return save_figure(fig, output, "04-dev-layer-selection"), source_rows


def direction_alignment(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.7), sharey=True)
    source_rows: list[dict[str, Any]] = []
    for ax, state_row in zip(axes, sources["probe_fit"]["states"], strict=True):
        state = state_row["state"]
        cells = state_row["cells"]
        layers = [int(cell["layer"]) for cell in cells]
        means = [float(cell["direction"]["mean_pairwise_cosine"]) for cell in cells]
        minima = [float(cell["direction"]["min_pairwise_cosine"]) for cell in cells]
        ax.plot(
            layers, means, color=COLORS["blue"], marker="o", markersize=3.5, label="Mean cosine"
        )
        ax.plot(
            layers,
            minima,
            color=COLORS["orange"],
            marker="s",
            markersize=3.2,
            label="Minimum cosine",
        )
        ax.axhline(0.4, color=COLORS["red"], linestyle="--", label="Required mean: 0.40")
        ax.axhline(0.0, color=COLORS["gray"], linestyle=":", label="Required minimum: 0.00")
        ax.set_title(STATE_LABELS[state].replace("\n", " "))
        ax.set_ylim(-0.35, 0.55)
        ax.grid(alpha=0.18)
        ax.text(
            0.5,
            0.04,
            "No aligned layer",
            transform=ax.transAxes,
            ha="center",
            fontsize=8.5,
            color=COLORS["red"],
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
        )
        source_rows.extend(
            {
                "state": state,
                "layer": layer,
                "mean_pairwise_cosine": mean,
                "minimum_pairwise_cosine": minimum,
                "aligned": False,
            }
            for layer, mean, minimum in zip(layers, means, minima, strict=True)
        )
    axes[0].set_ylabel("Task-level A/B direction cosine")
    axes[0].legend(loc="upper left", fontsize=7.8, frameon=True, facecolor="white", framealpha=0.9)
    fig.supxlabel("Layer", y=0.055)
    fig.suptitle(
        "Task-level policy-orientation directions did not align",
        fontsize=17,
        fontweight="bold",
    )
    add_note(
        fig,
        "Direction alignment uses one A/B difference vector per training task only; probe "
        "fitting separately uses all activation rows with equal total weight per task-policy "
        "group.",
    )
    return save_figure(fig, output, "05-task-direction-alignment"), source_rows


def quadrant_support(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    dataset = sources["activation_dataset"]
    report = sources["report"]
    by_split = dataset["quadrant_counts_by_split"]
    split_order = ("train", "dev", "test")
    quadrant_colors = (
        COLORS["green"],
        COLORS["red"],
        COLORS["purple"],
        COLORS["orange"],
    )
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2), gridspec_kw={"width_ratios": (1.25, 1)})
    x = np.arange(3)
    bottom = np.zeros(3)
    source_rows: list[dict[str, Any]] = []
    totals = [sum(int(by_split[split][q]) for q in QUADRANT_ORDER) for split in split_order]
    for quadrant, color in zip(QUADRANT_ORDER, quadrant_colors, strict=True):
        values = np.array(
            [
                int(by_split[split][quadrant]) / totals[index]
                for index, split in enumerate(split_order)
            ]
        )
        axes[0].bar(x, values, bottom=bottom, color=color, label=QUADRANT_LABELS[quadrant])
        for index, (value, base) in enumerate(zip(values, bottom, strict=True)):
            count = int(by_split[split_order[index]][quadrant])
            if value >= 0.08:
                axes[0].text(
                    index, base + value / 2, str(count), ha="center", va="center", fontsize=8
                )
            source_rows.append(
                {
                    "panel": "quadrants_by_split",
                    "split": split_order[index],
                    "quadrant": quadrant,
                    "count": count,
                    "split_total": totals[index],
                    "rate": value,
                }
            )
        bottom += values
    axes[0].set_title("A. Behavioral/visibility quadrants")
    axes[0].set_ylabel("Share of audited plans")
    axes[0].set_xticks(
        x, [f"Train\n(n={totals[0]})", f"Dev\n(n={totals[1]})", f"Test\n(n={totals[2]})"]
    )
    axes[0].set_ylim(0, 1)
    axes[0].set_yticks(np.linspace(0, 1, 6), [f"{value:.0%}" for value in np.linspace(0, 1, 6)])
    axes[0].grid(axis="y", alpha=0.18)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper left",
        bbox_to_anchor=(0.02, 0.91),
        ncol=2,
        fontsize=8,
    )

    primary = report["primary_renderer_ingestion_analysis"]
    support_rows = (
        ("Omitted/blurred", int(primary["omitted_or_blurred"]["rows"]), True),
        ("Hidden use", int(primary["hidden_use"]["rows"]), False),
        ("False certificate", int(primary["false_certificate"]["rows"]), True),
    )
    bars = axes[1].bar(
        np.arange(3),
        [row_count for _, row_count, _ in support_rows],
        color=[COLORS["green"] if supported else COLORS["red"] for _, _, supported in support_rows],
    )
    axes[1].axhline(10, color=COLORS["dark"], linestyle="--", label="Minimum support: 10")
    for bar, (_, row_count, supported) in zip(bars, support_rows, strict=True):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            row_count + 0.6,
            f"{row_count}\n{'supported' if supported else 'insufficient'}",
            ha="center",
            fontsize=8.5,
        )
    axes[1].set_title("B. Held-out primary-subset support")
    axes[1].set_ylabel("Held-out rows")
    axes[1].set_xticks(np.arange(3), [label.replace(" ", "\n", 1) for label, _, _ in support_rows])
    axes[1].set_ylim(0, 28)
    axes[1].grid(axis="y", alpha=0.18)
    axes[1].legend(loc="upper right", fontsize=8)
    for label, row_count, supported in support_rows:
        source_rows.append(
            {
                "panel": "heldout_subset_support",
                "split": "test",
                "quadrant": label,
                "count": row_count,
                "split_total": 48,
                "rate": row_count / 48,
                "supported": supported,
            }
        )
    fig.suptitle("Stage 3 quadrant composition and support", fontsize=17, fontweight="bold")
    add_note(fig)
    return save_figure(fig, output, "06-quadrants-and-support", top=0.84), source_rows


def audit_quality(
    sources: dict[str, dict[str, Any]], output: Path
) -> tuple[list[Path], list[dict[str, Any]]]:
    dataset = sources["activation_dataset"]
    report = sources["report"]
    agreement = dataset["agreement"]
    labels = (
        "Clause selection\nagreement",
        "Clause selection\nκ",
        "Policy visibility\nagreement",
        "Policy visibility\nκ",
        "Clause selected\ncorrectly",
        "Policy visibly\nretained",
        "Confident wrong\nclause",
    )
    values = (
        float(agreement["clause_selection_agreement"]),
        float(agreement["clause_selection_kappa"]),
        float(agreement["policy_visibility_agreement"]),
        float(agreement["policy_visibility_kappa"]),
        float(report["clause_selection_correct_rate"]),
        float(report["visible_retention_rate"]),
        float(report["confident_wrong_clause_rate"]),
    )
    roles = ("agreement", "agreement", "agreement", "agreement", "audit", "audit", "audit")
    fig, ax = plt.subplots(figsize=(12.3, 6.2))
    colors = [COLORS["blue"]] * 4 + [COLORS["teal"]] * 2 + [COLORS["red"]]
    bars = ax.bar(np.arange(len(values)), values, color=colors)
    for index, (bar, value) in enumerate(zip(bars, values, strict=True)):
        label = f"κ={value:.3f}" if index in (1, 3) else f"{value:.1%}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            label,
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    ax.set_title("Behavior-blinded plan-audit reliability and outcomes")
    ax.set_ylabel("Agreement, kappa, or audited rate")
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.set_ylim(0, 1.04)
    ax.grid(axis="y", alpha=0.2)
    add_note(
        fig,
        "Independent double-audit covered 96 plans. Agreement was deemed reliable; all 240 "
        "plans were labeled, with no malformed plans or unlabeled rows.",
    )
    source_rows = [
        {"metric": label.replace("\n", " "), "value": value, "role": role}
        for label, value, role in zip(labels, values, roles, strict=True)
    ]
    return save_figure(fig, output, "07-plan-audit-quality"), source_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty source data: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_readme(output: Path) -> Path:
    path = output / "README.md"
    path.write_text(
        """# Stage 3 result figures

These figures are descriptive views of the immutable Stage 3 activation, audit, probe,
selection, held-out, and completion artifacts. The packet does not recompute or replace the
canonical Stage 3 report.

## Key result

`01-key-stage3-evidence` is the recommended main figure. It shows the held-out boundary probes,
the primary omitted/blurred renderer-ingestion analysis against text controls, and the frozen
Stage 4 authorization decision.

Suggested sentence beneath the figure:

> On the single held-out archive task, renderer-ingestion activations did not decode the assigned
> policy on omitted/blurred plans (AUROC 0.485), did not outperform the best text control, and did
> not yield an aligned cross-task policy-orientation direction, so Stage 4 was not authorized.

## Supporting figures

1. `02-heldout-probe-transfer`: pooled and disjoint-paraphrase probe performance by boundary.
2. `03-renderer-controls`: renderer activation versus text, metadata, and negative controls.
3. `04-dev-layer-selection`: dev-only layer-selection curves; these are not held-out evidence.
4. `05-task-direction-alignment`: task-level A/B direction cosines across layers.
5. `06-quadrants-and-support`: quadrant composition and held-out denominator support.
6. `07-plan-audit-quality`: behavior-blinded audit reliability and plan-label outcomes.

Each figure has PNG and SVG versions. The matching CSV contains its plotted source values.
`figure-manifest.json` records exact SHA-256 hashes for all canonical sources and generated files.

## Interpretation boundary

Stage 3 is a five-task pilot with only one dev task and one held-out test task. A negative Stage 3
result blocks the preregistered causal intervention; it does not invalidate the Stage 0 or Stage 1
behavioral findings. Pooled scores containing explicit policy text are localization diagnostics,
not the primary mechanistic result.
""",
        encoding="utf-8",
    )
    return path


def write_manifest(output: Path, generated: list[Path]) -> Path:
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "stage1_gate": "passed",
        "stage2_status": "valid_continuation",
        "stage3_status": "valid_continuation",
        "causal_evaluation_authorized": False,
        "pilot": True,
        "base_task_split": {"train": 3, "dev": 1, "test": 1},
        "generalization_claim": "none_single_heldout_task_case_study",
        "sources": [
            {"name": name, "path": str(path), "sha256": sha256(path)}
            for name, path in SOURCE_PATHS.items()
        ],
        "files": [
            {"path": str(path.relative_to(output)), "sha256": sha256(path)}
            for path in sorted(generated)
        ],
    }
    path = output / "figure-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    sources = load_sources()
    generators = (
        (key_evidence, "key-evidence.csv"),
        (probe_transfer, "heldout-probe-transfer.csv"),
        (renderer_controls, "renderer-controls.csv"),
        (dev_layer_sweep, "dev-layer-selection.csv"),
        (direction_alignment, "task-direction-alignment.csv"),
        (quadrant_support, "quadrants-and-support.csv"),
        (audit_quality, "plan-audit-quality.csv"),
    )
    generated: list[Path] = []
    for generator, csv_name in generators:
        figures, rows = generator(sources, output)
        generated.extend(figures)
        csv_path = output / csv_name
        write_csv(csv_path, rows)
        generated.append(csv_path)
    generated.append(write_readme(output))
    manifest = write_manifest(output, generated)
    print(
        json.dumps(
            {
                "output_directory": str(output),
                "generated_files": len(generated) + 1,
                "manifest": str(manifest),
            },
            indent=2,
        )
    )
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
