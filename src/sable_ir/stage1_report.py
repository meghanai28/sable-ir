"""Stage 1E continuation gates and auditable final report."""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, TypeVar

from pydantic import Field

from sable_ir.schema import StrictModel
from sable_ir.stage1 import Stage1Error
from sable_ir.stage1_analysis import (
    BehavioralMetrics,
    BehavioralRow,
    LengthMatch,
    LengthReport,
    PlanAudit,
    PolicyVisibility,
)
from sable_ir.stage1_controls import ControlPlanKind, validate_control_plan_audit

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"
    NOT_EVALUABLE = "not_evaluable"
    INSUFFICIENT_CONTROL_SUPPORT = "insufficient_control_support"
    DESCRIPTIVE = "descriptive"


class Stage1Recommendation(StrEnum):
    INCOMPLETE = "incomplete"
    INVALID_TASK_OR_TESTS = "invalid_task_or_tests"
    INSUFFICIENT_CONTROL_SUPPORT = "insufficient_control_support"
    STOP_OR_PIVOT = "stop_or_pivot"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    CONTINUE_TO_STAGE2 = "continue_to_stage2"


class Stage1Thresholds(StrictModel):
    opposite_reversal_rate_min: float = 0.20
    control_jointly_functional_pairs_min: int = 60
    conditional_substitution_compliance_drop_min: float = 0.10
    clause_order_correct_selection_min: float = 0.50
    clause_order_natural_drop_max: float = 0.20
    supported_bin_matched_pairs_min: int = 10
    supported_bin_task_policy_groups_min: int = 4
    compression_trend_bins_min: int = 2
    nonlinear_analysis_bins_min: int = 3


class Stage1Gate(StrictModel):
    gate_id: str
    description: str
    status: GateStatus
    observed: float | int | None
    threshold: str | None
    detail: str
    eligible_pairs: int | None = None
    coverage_by_task_policy: dict[str, int] | None = None


class Stage1Report(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    scope: Literal["five_task_pilot"] = "five_task_pilot"
    stage0_report_sha256: Sha256
    natural_behavior_sha256: Sha256
    opposite_behavior_sha256: Sha256
    shuffled_behavior_sha256: Sha256
    wrong_clause_behavior_sha256: Sha256
    length_report_sha256: Sha256
    plan_audit_sha256: Sha256
    wrong_clause_control_audit_sha256: Sha256
    clause_order_control_audit_sha256: Sha256
    thresholds: Stage1Thresholds
    gates: tuple[Stage1Gate, ...]
    automatic_gates_passed: bool
    dataset_and_plan_audits_passed: bool
    compression_claim_scope: Literal[
        "no_length_comparison", "format_comparison_only", "compression_trend", "nonlinear_possible"
    ]
    recommendation: Stage1Recommendation
    mechanistic_scope_note: str


def build_stage1_report(
    stage0_report_path: Path,
    natural_behavior_path: Path,
    opposite_behavior_path: Path,
    shuffled_behavior_path: Path,
    wrong_clause_behavior_path: Path,
    length_report_path: Path,
    plan_audit_path: Path,
    wrong_clause_control_audit_path: Path,
    clause_order_control_audit_path: Path,
    control_plan_manifest_path: Path,
    output_path: Path,
    *,
    thresholds: Stage1Thresholds | None = None,
    final_manual_review_passed: bool = False,
) -> Stage1Report:
    """Evaluate VI.E with explicit thresholds and preserve the local-model scope boundary."""
    thresholds = thresholds or Stage1Thresholds()
    stage0 = _json(stage0_report_path)
    natural = _load(BehavioralMetrics, natural_behavior_path)
    opposite = _load(BehavioralMetrics, opposite_behavior_path)
    shuffled = _load(BehavioralMetrics, shuffled_behavior_path)
    wrong = _load(BehavioralMetrics, wrong_clause_behavior_path)
    lengths = _load(LengthReport, length_report_path)
    audit = _load(PlanAudit, plan_audit_path)
    wrong_control_audit = validate_control_plan_audit(
        wrong_clause_control_audit_path,
        control_plan_manifest_path,
        ControlPlanKind.WRONG_CLAUSE,
    )
    order_control_audit = validate_control_plan_audit(
        clause_order_control_audit_path,
        control_plan_manifest_path,
        ControlPlanKind.CLAUSE_ORDER,
    )
    gates = _gates(
        stage0,
        natural,
        opposite,
        shuffled,
        wrong,
        lengths,
        audit,
        wrong_control_audit,
        order_control_audit,
        thresholds,
    )
    invalid = any(gate.status is GateStatus.INVALID for gate in gates)
    incomplete = any(gate.status is GateStatus.NOT_EVALUABLE for gate in gates)
    insufficient = any(
        gate.status is GateStatus.INSUFFICIENT_CONTROL_SUPPORT for gate in gates
    )
    failed = any(gate.status is GateStatus.FAILED for gate in gates)
    automatic_passed = not (invalid or incomplete or insufficient or failed)
    shared_bins = len(_supported_length_bins(lengths, thresholds))
    compression_scope: Literal[
        "no_length_comparison", "format_comparison_only", "compression_trend", "nonlinear_possible"
    ]
    if shared_bins >= thresholds.nonlinear_analysis_bins_min:
        compression_scope = "nonlinear_possible"
    elif shared_bins >= thresholds.compression_trend_bins_min:
        compression_scope = "compression_trend"
    elif shared_bins == 1:
        compression_scope = "format_comparison_only"
    else:
        compression_scope = "no_length_comparison"
    if incomplete:
        recommendation = Stage1Recommendation.INCOMPLETE
    elif invalid:
        recommendation = Stage1Recommendation.INVALID_TASK_OR_TESTS
    elif insufficient:
        recommendation = Stage1Recommendation.INSUFFICIENT_CONTROL_SUPPORT
    elif failed:
        recommendation = Stage1Recommendation.STOP_OR_PIVOT
    elif not final_manual_review_passed:
        recommendation = Stage1Recommendation.MANUAL_REVIEW_REQUIRED
    else:
        recommendation = Stage1Recommendation.CONTINUE_TO_STAGE2
    report = Stage1Report(
        created_at=_now(),
        stage0_report_sha256=_sha(stage0_report_path.read_bytes()),
        natural_behavior_sha256=_sha(natural_behavior_path.read_bytes()),
        opposite_behavior_sha256=_sha(opposite_behavior_path.read_bytes()),
        shuffled_behavior_sha256=_sha(shuffled_behavior_path.read_bytes()),
        wrong_clause_behavior_sha256=_sha(wrong_clause_behavior_path.read_bytes()),
        length_report_sha256=_sha(length_report_path.read_bytes()),
        plan_audit_sha256=_sha(plan_audit_path.read_bytes()),
        wrong_clause_control_audit_sha256=_sha(
            wrong_clause_control_audit_path.read_bytes()
        ),
        clause_order_control_audit_sha256=_sha(
            clause_order_control_audit_path.read_bytes()
        ),
        thresholds=thresholds,
        gates=tuple(gates),
        automatic_gates_passed=automatic_passed,
        dataset_and_plan_audits_passed=final_manual_review_passed,
        compression_claim_scope=compression_scope,
        recommendation=recommendation,
        mechanistic_scope_note=(
            "Stage 1 is hosted-Kimi behavioral evidence only. Before activation probing or "
            "causal intervention, reproduce the phenomenon on the selected local open-weight "
            "model; all mechanistic conclusions apply only to that local model."
        ),
    )
    _write_new(output_path, report.model_dump_json(indent=2) + "\n")
    return report


def _gates(
    stage0: dict[str, object],
    natural: BehavioralMetrics,
    opposite: BehavioralMetrics,
    shuffled: BehavioralMetrics,
    wrong: BehavioralMetrics,
    lengths: LengthReport,
    audit: PlanAudit,
    wrong_control_audit: dict[str, int | float],
    order_control_audit: dict[str, int | float],
    thresholds: Stage1Thresholds,
) -> list[Stage1Gate]:
    expected_counts = ((natural, 720), (opposite, 120), (shuffled, 120), (wrong, 120))
    if any(metric.evaluated_rows != expected for metric, expected in expected_counts):
        return [
            Stage1Gate(
                gate_id="S1-COMPLETE",
                description="All natural and control renderer outputs evaluated",
                status=GateStatus.NOT_EVALUABLE,
                observed=min(
                    metric.evaluated_rows for metric, _expected in expected_counts
                ),
                threshold="720 natural and 120 in each stratified control",
                detail=(
                    "Missing jobs or infrastructure errors make Stage 1 incomplete and retryable."
                ),
            )
        ]
    mutual = sum(
        row.functionality.value == "pass"
        and row.policy_a.value == "pass"
        and row.policy_b.value == "pass"
        for metric in (natural, opposite, shuffled, wrong)
        for row in metric.rows
    )
    if mutual:
        return [
            Stage1Gate(
                gate_id="S1-INTEGRITY",
                description="Mutually exclusive policy-suite integrity",
                status=GateStatus.INVALID,
                observed=mutual,
                threshold="0",
                detail=(
                    "Any functional output passing both suites indicates invalid tasks or tests."
                ),
            )
        ]
    complete_audit = all(row.complete for row in audit.rows)
    if not complete_audit:
        return [
            Stage1Gate(
                gate_id="S1-AUDIT",
                description="Behavior-blinded plan audit completeness",
                status=GateStatus.NOT_EVALUABLE,
                observed=sum(row.complete for row in audit.rows),
                threshold="180",
                detail="VG and clause-selection gates require all blinded plan labels.",
            )
        ]
    derived = stage0.get("derived")
    if not isinstance(derived, dict):
        raise Stage1Error("Stage 0 report lacks derived metrics")
    direct_functionality = float(derived["full_functional_rate"])
    direct_compliance = float(derived["full_assigned_policy_given_functional_rate"])
    full_structured = [
        row
        for row in natural.rows
        if row.plan_format.value == "structured" and row.nominal_concision == "full"
    ]
    structured_functionality = _mean(
        [row.functionality.value == "pass" for row in full_structured]
    )
    functional_structured = [row for row in full_structured if row.functionality.value == "pass"]
    structured_compliance = _mean(
        [row.assigned_policy_and_functional for row in functional_structured]
    )
    opposite_reversal, opposite_pairs, opposite_coverage = _exact_opposite_reversal(
        natural, opposite
    )
    valid_matches = _valid_length_matches_by_group(lengths)
    supported_bins = _supported_length_bins(lengths, thresholds)
    natural_selection = sum(
        row.clause_selection is not None and row.clause_selection.value == "correct"
        for row in audit.rows
    ) / len(audit.rows)
    reordered_selection = float(
        order_control_audit["clause_order_correct_selection_rate"]
    )
    valid_wrong = float(wrong_control_audit["wrong_clause_plan_valid_rate"])
    selection_by_bin = _selection_by_bin(audit, lengths)
    compliance_by_bin = _compliance_by_bin(natural, lengths)
    shared_bin_count = len(supported_bins)
    nonsaturated = _has_headroom(selection_by_bin) and _has_headroom(compliance_by_bin)
    wrong_drop, wrong_pairs, wrong_coverage = _conditional_control_drop(natural, wrong)
    shuffled_drop, shuffled_pairs, shuffled_coverage = _conditional_control_drop(
        natural, shuffled
    )
    visible_omissions = sum(
        row.policy_visibility is not PolicyVisibility.PRESERVED for row in audit.rows
    )
    return [
        _descriptive_difference(
            "S1.1a",
            "Full structured functionality versus sparse Stage 0 full-document direct",
            structured_functionality,
            direct_functionality,
        ),
        _descriptive_difference(
            "S1.1b",
            "Full structured compliance versus sparse Stage 0 full-document direct",
            structured_compliance,
            direct_compliance,
        ),
        _supported_minimum_gate(
            "S1.2",
            "Opposite-policy plans cause exact assigned-only to opposite-only reversal",
            opposite_reversal,
            opposite_pairs,
            opposite_coverage,
            thresholds.opposite_reversal_rate_min,
            thresholds.control_jointly_functional_pairs_min,
        ),
        _conditional_drop_gate(
            "S1.3",
            "Wrong-clause plans reduce assigned-policy compliance among jointly functional pairs",
            wrong_drop,
            wrong_pairs,
            wrong_coverage,
            thresholds.conditional_substitution_compliance_drop_min,
            thresholds.control_jointly_functional_pairs_min,
            valid_control=valid_wrong == 1.0,
        ),
        _functionality_diagnostic("S1.3F", natural, wrong, "wrong-clause"),
        Stage1Gate(
            gate_id="S1.4",
            description="Reversing clause order does not determine clause selection",
            status=(
                GateStatus.PASSED
                if reordered_selection >= thresholds.clause_order_correct_selection_min
                and natural_selection - reordered_selection
                <= thresholds.clause_order_natural_drop_max
                else GateStatus.FAILED
            ),
            observed=reordered_selection,
            threshold=(
                f">= {thresholds.clause_order_correct_selection_min:.0%} and natural drop "
                f"<= {thresholds.clause_order_natural_drop_max:.0%}"
            ),
            detail=f"Natural correct selection was {natural_selection:.1%}.",
        ),
        _descriptive_control_drop(
            "S1.5",
            "Shuffled-task conditional policy-compliance drop",
            shuffled_drop,
            shuffled_pairs,
            shuffled_coverage,
        ),
        _functionality_diagnostic("S1.5F", natural, shuffled, "shuffled-task"),
        Stage1Gate(
            gate_id="S1.6",
            description="Structured and free-form plans overlap in observed length",
            status=(
                GateStatus.PASSED
                if supported_bins
                else GateStatus.FAILED
            ),
            observed=len(supported_bins),
            threshold=(
                f">= 1 bin with >= {thresholds.supported_bin_matched_pairs_min} strict matches "
                f"spanning >= {thresholds.supported_bin_task_policy_groups_min} task-policy groups"
            ),
            detail=(
                "A strict match is in the same bin and differs by no more than max(5 tokens, "
                f"10% of the shorter plan). Supported bins={supported_bins}; "
                f"strict matches by group={valid_matches}."
            ),
        ),
        Stage1Gate(
            gate_id="S1.7",
            description="Evidence tier for compression-versus-length analysis",
            status=(
                GateStatus.PASSED
                if shared_bin_count >= thresholds.compression_trend_bins_min and nonsaturated
                else GateStatus.DESCRIPTIVE
                if shared_bin_count == 1
                else GateStatus.FAILED
            ),
            observed=shared_bin_count,
            threshold=(
                f">= {thresholds.compression_trend_bins_min} shared bins for a trend; "
                f">= {thresholds.nonlinear_analysis_bins_min} for nonlinear/crossover analysis"
            ),
            detail=(
                f"Selection bins={selection_by_bin}; assigned-functional bins={compliance_by_bin}. "
                "Exactly one shared bin permits format comparison only."
            ),
        ),
        Stage1Gate(
            gate_id="S1.8",
            description="Natural plans include visible omissions, blurs, or replacements",
            status=GateStatus.PASSED,
            observed=visible_omissions,
            threshold=None,
            detail=(
                "Natural loss cases are available."
                if visible_omissions
                else "No natural omission occurred; retain the compression frontier and use the "
                "matched A/B counterfactual route, as specified by VI.E.9."
            ),
        ),
    ]


def _descriptive_difference(
    gate_id: str, description: str, observed: float, reference: float
) -> Stage1Gate:
    difference = abs(observed - reference)
    return Stage1Gate(
        gate_id=gate_id,
        description=description,
        status=GateStatus.DESCRIPTIVE,
        observed=difference,
        threshold=None,
        detail=(
            f"Stage 1={observed:.1%}; sparse Stage 0 direct={reference:.1%}. "
            "No stop decision is made from this difference."
        ),
    )


def _supported_minimum_gate(
    gate_id: str,
    description: str,
    observed: float | None,
    eligible_pairs: int,
    coverage: dict[str, int],
    threshold: float,
    denominator_min: int,
) -> Stage1Gate:
    return Stage1Gate(
        gate_id=gate_id,
        description=description,
        status=(
            GateStatus.INSUFFICIENT_CONTROL_SUPPORT
            if eligible_pairs < denominator_min
            else GateStatus.PASSED
            if observed is not None and observed >= threshold
            else GateStatus.FAILED
        ),
        observed=observed,
        threshold=f">= {threshold:.0%}",
        detail=(
            f"Exact reversals among {eligible_pairs} matched pairs where both outputs are "
            "functional; coverage is reported by task-policy group."
        ),
        eligible_pairs=eligible_pairs,
        coverage_by_task_policy=coverage,
    )


def _conditional_drop_gate(
    gate_id: str,
    description: str,
    drop: float | None,
    jointly_functional_pairs: int,
    coverage: dict[str, int],
    threshold: float,
    denominator_min: int,
    *,
    valid_control: bool = True,
) -> Stage1Gate:
    return Stage1Gate(
        gate_id=gate_id,
        description=description,
        status=(
            GateStatus.INVALID
            if not valid_control
            else GateStatus.INSUFFICIENT_CONTROL_SUPPORT
            if jointly_functional_pairs < denominator_min
            else GateStatus.PASSED
            if drop is not None and drop >= threshold
            else GateStatus.FAILED
        ),
        observed=drop,
        threshold=f">= {threshold:.0%} absolute drop with >= {denominator_min} eligible pairs",
        detail=(
            f"Computed only over {jointly_functional_pairs} matched pairs where both outputs "
            "passed functionality."
        ),
        eligible_pairs=jointly_functional_pairs,
        coverage_by_task_policy=coverage,
    )


def _descriptive_control_drop(
    gate_id: str,
    description: str,
    drop: float | None,
    eligible_pairs: int,
    coverage: dict[str, int],
) -> Stage1Gate:
    return Stage1Gate(
        gate_id=gate_id,
        description=description,
        status=GateStatus.DESCRIPTIVE,
        observed=drop,
        threshold=None,
        detail=(
            f"Descriptive only; computed over {eligible_pairs} pairs where both natural and "
            "shuffled outputs passed functionality. Functionality loss is reported separately."
        ),
        eligible_pairs=eligible_pairs,
        coverage_by_task_policy=coverage,
    )


def _functionality_diagnostic(
    gate_id: str,
    natural: BehavioralMetrics,
    control: BehavioralMetrics,
    label: str,
) -> Stage1Gate:
    natural_by_id = {row.job_id: row for row in natural.rows}
    paired = [(natural_by_id[row.job_id], row) for row in control.rows]
    natural_rate = _mean([a.functionality.value == "pass" for a, _b in paired])
    control_rate = _mean([b.functionality.value == "pass" for _a, b in paired])
    return Stage1Gate(
        gate_id=gate_id,
        description=f"{label} functionality-loss diagnostic",
        status=GateStatus.DESCRIPTIVE,
        observed=natural_rate - control_rate,
        threshold=None,
        detail=f"Matched natural={natural_rate:.1%}; control={control_rate:.1%}.",
    )


def _conditional_control_drop(
    natural: BehavioralMetrics, control: BehavioralMetrics
) -> tuple[float | None, int, dict[str, int]]:
    natural_by_id = {row.job_id: row for row in natural.rows}
    jointly_functional = [
        (natural_by_id[row.job_id], row)
        for row in control.rows
        if natural_by_id[row.job_id].functionality.value == "pass"
        and row.functionality.value == "pass"
    ]
    coverage = _pair_coverage(jointly_functional)
    if not jointly_functional:
        return None, 0, coverage
    natural_rate = _mean([a.assigned_policy_and_functional for a, _b in jointly_functional])
    control_rate = _mean([b.assigned_policy_and_functional for _a, b in jointly_functional])
    return natural_rate - control_rate, len(jointly_functional), coverage


def _exact_opposite_reversal(
    natural: BehavioralMetrics, opposite: BehavioralMetrics
) -> tuple[float | None, int, dict[str, int]]:
    natural_by_id = {row.job_id: row for row in natural.rows}
    eligible = [
        (natural_by_id[row.job_id], row)
        for row in opposite.rows
        if natural_by_id[row.job_id].functionality.value == "pass"
        and row.functionality.value == "pass"
    ]
    reversals = [
        _follows_assigned_only(a) and _follows_opposite_only(b) for a, b in eligible
    ]
    return (_mean(reversals) if reversals else None, len(eligible), _pair_coverage(eligible))


def _follows_assigned_only(row: BehavioralRow) -> bool:
    policy_a = row.policy_a.value == "pass"
    policy_b = row.policy_b.value == "pass"
    return (
        policy_a and not policy_b
        if row.assigned_policy.value == "A"
        else policy_b and not policy_a
    )


def _follows_opposite_only(row: BehavioralRow) -> bool:
    policy_a = row.policy_a.value == "pass"
    policy_b = row.policy_b.value == "pass"
    return (
        policy_b and not policy_a
        if row.assigned_policy.value == "A"
        else policy_a and not policy_b
    )


def _pair_coverage(pairs: list[tuple[BehavioralRow, BehavioralRow]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for natural, _control in pairs:
        counts[f"{natural.task_id}:{natural.assigned_policy.value}"] += 1
    return dict(sorted(counts.items()))


def _valid_length_matches_by_group(lengths: LengthReport) -> dict[str, int]:
    bins = {row.job_id: row.observed_length_bin for row in lengths.rows}
    counts: dict[str, int] = defaultdict(int)
    for match in lengths.nearest_length_matches:
        key = f"{match.task_id}:{match.assigned_policy.value}"
        allowed = max(5.0, 0.10 * min(match.structured_tokens, match.freeform_tokens))
        if (
            bins[match.structured_job_id] == bins[match.freeform_job_id]
            and match.absolute_token_difference <= allowed
        ):
            counts[key] += 1
    for row in lengths.rows:
        counts.setdefault(f"{row.task_id}:{row.assigned_policy.value}", 0)
    return dict(sorted(counts.items()))


def _supported_length_bins(
    lengths: LengthReport, thresholds: Stage1Thresholds
) -> dict[str, dict[str, object]]:
    bins = {row.job_id: row.observed_length_bin for row in lengths.rows}
    support: dict[str, list[LengthMatch]] = defaultdict(list)
    for match in lengths.nearest_length_matches:
        allowed = max(5.0, 0.10 * min(match.structured_tokens, match.freeform_tokens))
        if (
            bins[match.structured_job_id] == bins[match.freeform_job_id]
            and match.absolute_token_difference <= allowed
        ):
            support[bins[match.structured_job_id]].append(match)
    result: dict[str, dict[str, object]] = {}
    for bin_name, matches in sorted(support.items()):
        groups = {f"{item.task_id}:{item.assigned_policy.value}" for item in matches}
        if (
            len(matches) >= thresholds.supported_bin_matched_pairs_min
            and len(groups) >= thresholds.supported_bin_task_policy_groups_min
        ):
            result[bin_name] = {"matched_pairs": len(matches), "task_policy_groups": sorted(groups)}
    return result


def _selection_by_bin(audit: PlanAudit, lengths: LengthReport) -> dict[str, float]:
    bins = {row.job_id: row.observed_length_bin for row in lengths.rows}
    values: dict[str, list[bool]] = defaultdict(list)
    for row in audit.rows:
        values[bins[row.job_id]].append(
            row.clause_selection is not None and row.clause_selection.value == "correct"
        )
    return {key: _mean(items) for key, items in sorted(values.items())}


def _compliance_by_bin(
    metrics: BehavioralMetrics, lengths: LengthReport
) -> dict[str, float]:
    bins = {row.job_id: row.observed_length_bin for row in lengths.rows}
    values: dict[str, list[bool]] = defaultdict(list)
    for row in metrics.rows:
        values[bins[row.source_plan_job_id]].append(row.assigned_policy_and_functional)
    return {key: _mean(items) for key, items in sorted(values.items())}


def _has_headroom(values: dict[str, float]) -> bool:
    return any(0.0 < value < 1.0 for value in values.values())


def _mean(values: list[bool]) -> float:
    if not values:
        raise Stage1Error("cannot aggregate an empty Stage 1 gate subset")
    return sum(values) / len(values)


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Stage1Error(f"could not load Stage 1 report input {path}: {error}") from error
    if not isinstance(value, dict):
        raise Stage1Error(f"Stage 1 report input is not an object: {path}")
    return value


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Stage1Error(f"could not validate Stage 1 report input {path}: {error}") from error


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise Stage1Error(f"could not create immutable Stage 1 report {path}: {error}") from error


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
