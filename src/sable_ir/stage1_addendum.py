"""Post-primary descriptive robustness report for Stage 1."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, TypeVar

from pydantic import Field

from sable_ir.schema import PolicyValue, StrictModel
from sable_ir.scoring import RawOutcome
from sable_ir.stage1 import RenderManifest, Stage1Error, load_render_manifest
from sable_ir.stage1_analysis import BehavioralMetrics, BehavioralRow
from sable_ir.stage1_controls import (
    ControlPlanAudit,
    ControlPlanKind,
    validate_control_plan_audit,
)
from sable_ir.stage1_report import Stage1Recommendation, Stage1Report

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)


class RobustnessConditionSummary(StrictModel):
    samples: int
    natural_functional: int
    controlled_functional: int
    functionality_change: float
    natural_assigned_policy_pass: int
    controlled_assigned_policy_pass: int
    assigned_policy_pass_change: float
    natural_assigned_policy_and_functional: int
    controlled_assigned_policy_and_functional: int
    assigned_policy_and_functional_change: float


class RobustnessPairRow(StrictModel):
    base_cell_id: str
    render_job_id: str
    task_id: str
    assigned_policy: PolicyValue
    plan_format: str
    concision: str
    natural_functional: bool
    natural_assigned_policy_pass: bool
    natural_assigned_policy_and_functional: bool
    clause_order_source_plan_job_id: str
    clause_order_applicable_clause_selected: bool
    clause_order_assigned_policy_distinction_retained: bool
    clause_order_functional: bool
    clause_order_assigned_policy_pass: bool
    clause_order_assigned_policy_and_functional: bool
    shuffled_source_plan_job_id: str
    shuffled_source_task_id: str
    shuffled_functional: bool
    shuffled_assigned_policy_pass: bool
    shuffled_assigned_policy_and_functional: bool


class Stage1RobustnessAddendum(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    role: Literal["post_primary_outcome_unseen_descriptive_robustness"] = (
        "post_primary_outcome_unseen_descriptive_robustness"
    )
    modifies_primary_stage1_gate: Literal[False] = False
    effect_size_stop_gate: None = None
    selection_sha256: Sha256
    canonical_stage1_report_sha256: Sha256
    natural_behavior_sha256: Sha256
    control_plan_manifest_sha256: Sha256
    clause_order_audit_sha256: Sha256
    clause_order_render_manifest_sha256: Sha256
    clause_order_behavior_sha256: Sha256
    shuffled_render_manifest_sha256: Sha256
    shuffled_behavior_sha256: Sha256
    expected_rows_per_condition: Literal[24] = 24
    evaluated_clause_order_rows: int
    evaluated_shuffled_rows: int
    clause_order_applicable_selection_numerator: int
    clause_order_applicable_selection_denominator: int
    clause_order_applicable_selection_rate: float
    clause_order_policy_distinction_numerator: int
    clause_order_policy_distinction_denominator: int
    clause_order_policy_distinction_rate: float
    clause_order: RobustnessConditionSummary
    shuffled_task: RobustnessConditionSummary
    cumulative_stage1_code_outputs: Literal[852] = 852
    rows: tuple[RobustnessPairRow, ...]
    interpretation: tuple[str, ...]


class Stage1OutputAccounting(StrictModel):
    natural: Literal[720] = 720
    opposite_policy: Literal[60] = 60
    wrong_clause: Literal[24] = 24
    clause_order: Literal[24] = 24
    shuffled_task: Literal[24] = 24
    total: Literal[852] = 852


class Stage1CompletionReportV2(StrictModel):
    """Canonical, self-contained Stage 1 evidence packet without rewriting v1."""

    schema_version: Literal[2] = 2
    created_at: str
    status: Literal["complete"] = "complete"
    recommendation: Literal[Stage1Recommendation.CONTINUE_TO_STAGE2] = (
        Stage1Recommendation.CONTINUE_TO_STAGE2
    )
    primary_stage1_report_path: str
    primary_stage1_report_sha256: Sha256
    robustness_addendum_path: str
    robustness_addendum_sha256: Sha256
    primary_report: Stage1Report
    robustness_addendum: Stage1RobustnessAddendum
    robustness_controls_added_after_primary_outcome: Literal[True] = True
    primary_progression_gate_modified: Literal[False] = False
    robustness_effect_size_stop_gate: None = None
    output_accounting: Stage1OutputAccounting
    primary_progression_basis: str
    robustness_support: tuple[str, ...]
    supported_behavioral_claim: str
    prohibited_claims: tuple[str, ...]


def build_stage1_completion_report_v2(
    primary_report_path: Path,
    robustness_addendum_path: Path,
    output_path: Path,
) -> Stage1CompletionReportV2:
    """Bind frozen primary and post-primary evidence into a new immutable v2 packet."""
    primary = _load(Stage1Report, primary_report_path)
    addendum = _load(Stage1RobustnessAddendum, robustness_addendum_path)
    primary_sha256 = _sha(primary_report_path.read_bytes())
    addendum_sha256 = _sha(robustness_addendum_path.read_bytes())
    if primary.recommendation is not Stage1Recommendation.CONTINUE_TO_STAGE2:
        raise Stage1Error("Stage 1 v2 requires an approved primary Stage 1 report")
    if addendum.canonical_stage1_report_sha256 != primary_sha256:
        raise Stage1Error("Stage 1 robustness addendum references another primary report")
    if addendum.modifies_primary_stage1_gate or addendum.effect_size_stop_gate is not None:
        raise Stage1Error("post-primary robustness evidence cannot modify the primary gate")
    if (
        addendum.evaluated_clause_order_rows != 24
        or addendum.evaluated_shuffled_rows != 24
        or addendum.cumulative_stage1_code_outputs != 852
    ):
        raise Stage1Error("Stage 1 robustness addendum is incomplete")
    report = Stage1CompletionReportV2(
        created_at=datetime.now(UTC).isoformat(),
        primary_stage1_report_path=primary_report_path.as_posix(),
        primary_stage1_report_sha256=primary_sha256,
        robustness_addendum_path=robustness_addendum_path.as_posix(),
        robustness_addendum_sha256=addendum_sha256,
        primary_report=primary,
        robustness_addendum=addendum,
        output_accounting=Stage1OutputAccounting(),
        primary_progression_basis=(
            "The prospectively frozen opposite-policy substitution gate remains the sole "
            "Stage 1 progression gate; the post-primary controls do not alter it."
        ),
        robustness_support=(
            "Clause-order was prospectively expected to be stable for the 24 frozen cells; "
            "applicable-clause selection and A/B distinction were retained in 24/24 plans, "
            "with assigned-policy-and-functional behavior changing from 20/24 to 21/24.",
            "Shuffled-task substitution was prospectively expected to be disruptive for the "
            "same 24 frozen cells; assigned-policy-and-functional behavior changed from "
            "20/24 to 6/24.",
            "These are qualitative supporting robustness criteria, not retrospectively "
            "selected numerical stop gates.",
        ),
        supported_behavioral_claim=(
            "The renderer is sensitive to the semantic content of the visible plan rather "
            "than merely reacting to arbitrary prompt perturbations."
        ),
        prohibited_claims=(
            "Stage 1 establishes that the visible plan mediates behavior.",
            "Stage 1 establishes how the model uses the plan internally.",
            "Stage 1 alone supports a mechanistic conclusion.",
            "All 852 outputs were part of the original primary preregistration.",
        ),
    )
    _write_new(output_path, report.model_dump_json(indent=2) + "\n")
    return report


def build_stage1_robustness_addendum(
    selection_path: Path,
    canonical_stage1_report_path: Path,
    natural_behavior_path: Path,
    control_plan_manifest_path: Path,
    clause_order_audit_path: Path,
    clause_order_render_manifest_path: Path,
    clause_order_behavior_path: Path,
    shuffled_render_manifest_path: Path,
    shuffled_behavior_path: Path,
    output_path: Path,
) -> Stage1RobustnessAddendum:
    """Aggregate the frozen descriptive addendum without changing Stage 1 gates."""
    selection = _json(selection_path)
    selection_sha256 = _sha(selection_path.read_bytes())
    if selection.get("status") != "frozen_before_addendum_outcomes":
        raise Stage1Error("robustness addendum selection was not frozen before outcomes")
    if selection.get("modifies_primary_stage1_gate") is not False:
        raise Stage1Error("robustness addendum cannot modify the primary Stage 1 gate")
    base_ids_value = selection.get("base_cell_ids")
    if not isinstance(base_ids_value, list) or len(base_ids_value) != 24:
        raise Stage1Error("robustness addendum requires 24 frozen base cells")
    base_ids = tuple(str(item) for item in base_ids_value)
    if len(set(base_ids)) != 24:
        raise Stage1Error("robustness addendum base cells are not unique")
    shuffled_definition = selection.get("shuffled_task")
    if not isinstance(shuffled_definition, dict):
        raise Stage1Error("robustness addendum lacks the shuffled-task definition")
    donor_value = shuffled_definition.get("target_to_source_task")
    if not isinstance(donor_value, dict):
        raise Stage1Error("robustness addendum lacks the frozen task derangement")
    donor_map = {str(key): str(value) for key, value in donor_value.items()}

    canonical = _load(Stage1Report, canonical_stage1_report_path)
    if canonical.recommendation is not Stage1Recommendation.CONTINUE_TO_STAGE2:
        raise Stage1Error("robustness addendum requires a frozen, approved Stage 1 report")
    natural = _load(BehavioralMetrics, natural_behavior_path)
    clause = _load(BehavioralMetrics, clause_order_behavior_path)
    shuffled = _load(BehavioralMetrics, shuffled_behavior_path)
    clause_manifest = load_render_manifest(clause_order_render_manifest_path)
    shuffled_manifest = load_render_manifest(shuffled_render_manifest_path)
    _validate_render_input(
        clause_manifest,
        clause,
        clause_order_render_manifest_path,
        selection_sha256,
        "clause_order",
    )
    _validate_render_input(
        shuffled_manifest,
        shuffled,
        shuffled_render_manifest_path,
        selection_sha256,
        "shuffled_task",
    )
    clause_audit = _load(ControlPlanAudit, clause_order_audit_path)
    audit_summary = validate_control_plan_audit(
        clause_order_audit_path,
        control_plan_manifest_path,
        ControlPlanKind.CLAUSE_ORDER,
    )
    if clause_audit.post_primary_selection_sha256 != selection_sha256:
        raise Stage1Error("clause-order audit references another addendum selection")
    if audit_summary["total"] != 24:
        raise Stage1Error("clause-order audit does not cover all 24 frozen cells")

    natural_rows = {row.job_id: row for row in natural.rows}
    clause_rows = {row.job_id: row for row in clause.rows}
    shuffled_rows = {row.job_id: row for row in shuffled.rows}
    clause_jobs = {job.job_id: job for job in clause_manifest.jobs}
    shuffled_jobs = {job.job_id: job for job in shuffled_manifest.jobs}
    audit_by_target = {row.target_plan_job_id: row for row in clause_audit.rows}
    rows: list[RobustnessPairRow] = []
    for base_id in base_ids:
        render_id = base_id.replace("__plan_", "__render_") + "__r00"
        try:
            natural_row = natural_rows[render_id]
            clause_row = clause_rows[render_id]
            shuffled_row = shuffled_rows[render_id]
            clause_job = clause_jobs[render_id]
            shuffled_job = shuffled_jobs[render_id]
            audit_row = audit_by_target[base_id]
        except KeyError as error:
            raise Stage1Error(f"robustness addendum lacks frozen cell {base_id}") from error
        expected_clause_source = f"{base_id}__control_clause_order"
        if clause_job.source_plan_job_id != expected_clause_source:
            raise Stage1Error(f"clause-order source mismatch for {base_id}")
        donor_task = donor_map[natural_row.task_id]
        expected_shuffled_source = base_id.replace(natural_row.task_id, donor_task, 1)
        if shuffled_job.source_plan_job_id != expected_shuffled_source:
            raise Stage1Error(f"shuffled-task source mismatch for {base_id}")
        if (
            audit_row.applicable_clause_selected is None
            or audit_row.assigned_policy_distinction_retained is None
        ):
            raise Stage1Error(f"clause-order audit is incomplete for {base_id}")
        rows.append(
            RobustnessPairRow(
                base_cell_id=base_id,
                render_job_id=render_id,
                task_id=natural_row.task_id,
                assigned_policy=natural_row.assigned_policy,
                plan_format=natural_row.plan_format.value,
                concision=natural_row.nominal_concision,
                natural_functional=_functional(natural_row),
                natural_assigned_policy_pass=_assigned_pass(natural_row),
                natural_assigned_policy_and_functional=(natural_row.assigned_policy_and_functional),
                clause_order_source_plan_job_id=clause_job.source_plan_job_id,
                clause_order_applicable_clause_selected=audit_row.applicable_clause_selected,
                clause_order_assigned_policy_distinction_retained=(
                    audit_row.assigned_policy_distinction_retained
                ),
                clause_order_functional=_functional(clause_row),
                clause_order_assigned_policy_pass=_assigned_pass(clause_row),
                clause_order_assigned_policy_and_functional=(
                    clause_row.assigned_policy_and_functional
                ),
                shuffled_source_plan_job_id=shuffled_job.source_plan_job_id,
                shuffled_source_task_id=donor_task,
                shuffled_functional=_functional(shuffled_row),
                shuffled_assigned_policy_pass=_assigned_pass(shuffled_row),
                shuffled_assigned_policy_and_functional=(
                    shuffled_row.assigned_policy_and_functional
                ),
            )
        )
    clause_selection = sum(row.clause_order_applicable_clause_selected for row in rows)
    clause_distinction = sum(row.clause_order_assigned_policy_distinction_retained for row in rows)
    report = Stage1RobustnessAddendum(
        created_at=datetime.now(UTC).isoformat(),
        selection_sha256=selection_sha256,
        canonical_stage1_report_sha256=_sha(canonical_stage1_report_path.read_bytes()),
        natural_behavior_sha256=_sha(natural_behavior_path.read_bytes()),
        control_plan_manifest_sha256=_sha(control_plan_manifest_path.read_bytes()),
        clause_order_audit_sha256=_sha(clause_order_audit_path.read_bytes()),
        clause_order_render_manifest_sha256=_sha(clause_order_render_manifest_path.read_bytes()),
        clause_order_behavior_sha256=_sha(clause_order_behavior_path.read_bytes()),
        shuffled_render_manifest_sha256=_sha(shuffled_render_manifest_path.read_bytes()),
        shuffled_behavior_sha256=_sha(shuffled_behavior_path.read_bytes()),
        evaluated_clause_order_rows=len(clause.rows),
        evaluated_shuffled_rows=len(shuffled.rows),
        clause_order_applicable_selection_numerator=clause_selection,
        clause_order_applicable_selection_denominator=len(rows),
        clause_order_applicable_selection_rate=clause_selection / len(rows),
        clause_order_policy_distinction_numerator=clause_distinction,
        clause_order_policy_distinction_denominator=len(rows),
        clause_order_policy_distinction_rate=clause_distinction / len(rows),
        clause_order=_condition_summary(rows, "clause_order"),
        shuffled_task=_condition_summary(rows, "shuffled_task"),
        rows=tuple(rows),
        interpretation=(
            "This addendum was frozen after the primary Stage 1 result and is descriptive only.",
            "Clause-order stability assesses planner robustness to irrelevant clause position.",
            "Shuffled-task disruption assesses whether the renderer can ignore a grossly "
            "mismatched plan.",
            "Neither condition changes, gates, or strengthens the primary Stage 1 causal language.",
        ),
    )
    _write_new(output_path, report.model_dump_json(indent=2) + "\n")
    return report


def _validate_render_input(
    manifest: RenderManifest,
    behavior: BehavioralMetrics,
    manifest_path: Path,
    selection_sha256: str,
    condition: Literal["clause_order", "shuffled_task"],
) -> None:
    if (
        manifest.condition != condition
        or manifest.design_variant != "post_primary_robustness"
        or manifest.post_primary_selection_sha256 != selection_sha256
        or len(manifest.jobs) != 24
        or behavior.expected_rows != 24
        or behavior.evaluated_rows != 24
        or behavior.render_manifest_sha256 != _sha(manifest_path.read_bytes())
    ):
        raise Stage1Error(f"incomplete or mismatched {condition} addendum input")


def _condition_summary(
    rows: list[RobustnessPairRow],
    condition: Literal["clause_order", "shuffled_task"],
) -> RobustnessConditionSummary:
    total = len(rows)
    natural_functional = sum(row.natural_functional for row in rows)
    natural_assigned = sum(row.natural_assigned_policy_pass for row in rows)
    natural_joint = sum(row.natural_assigned_policy_and_functional for row in rows)
    if condition == "clause_order":
        controlled_functional = sum(row.clause_order_functional for row in rows)
        controlled_assigned = sum(row.clause_order_assigned_policy_pass for row in rows)
        controlled_joint = sum(row.clause_order_assigned_policy_and_functional for row in rows)
    else:
        controlled_functional = sum(row.shuffled_functional for row in rows)
        controlled_assigned = sum(row.shuffled_assigned_policy_pass for row in rows)
        controlled_joint = sum(row.shuffled_assigned_policy_and_functional for row in rows)
    return RobustnessConditionSummary(
        samples=total,
        natural_functional=natural_functional,
        controlled_functional=controlled_functional,
        functionality_change=(controlled_functional - natural_functional) / total,
        natural_assigned_policy_pass=natural_assigned,
        controlled_assigned_policy_pass=controlled_assigned,
        assigned_policy_pass_change=(controlled_assigned - natural_assigned) / total,
        natural_assigned_policy_and_functional=natural_joint,
        controlled_assigned_policy_and_functional=controlled_joint,
        assigned_policy_and_functional_change=(controlled_joint - natural_joint) / total,
    )


def _assigned_pass(row: BehavioralRow) -> bool:
    outcome = row.policy_a if row.assigned_policy is PolicyValue.A else row.policy_b
    return outcome is RawOutcome.PASS


def _functional(row: BehavioralRow) -> bool:
    return row.functionality is RawOutcome.PASS


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Stage1Error(f"could not load robustness addendum input {path}: {error}") from error
    if not isinstance(value, dict):
        raise Stage1Error(f"robustness addendum input is not an object: {path}")
    return value


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Stage1Error(
            f"could not validate robustness addendum input {path}: {error}"
        ) from error


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise Stage1Error(
            f"could not create immutable robustness report {path}: {error}"
        ) from error


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
