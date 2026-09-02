from __future__ import annotations

from pathlib import Path

import pytest

from sable_ir.config import load_stage0_config
from sable_ir.generation import (
    GenerationManifest,
    GenerationStatus,
    prepare_stage0_run,
    run_stage0_generation,
)
from sable_ir.harness import HarnessUnavailable, RunStatus, UnsafeLocalSandbox
from sable_ir.provider import ModelRequest, ProviderResponse, TokenUsage
from sable_ir.schema import PolicyValue, Stage0Condition
from sable_ir.schema import TestSuiteKind as SuiteKind
from sable_ir.scoring import (
    DatasetAuditStatus,
    EvaluationArtifact,
    GateStatus,
    JobOutcome,
    OverallRecommendation,
    RawOutcome,
    ScoringError,
    build_dataset_audit_review,
    build_stage0_report,
    evaluate_generated_candidates,
    render_markdown,
    score_outcomes,
    write_stage0_report,
)


class ReferenceGenerationClient:
    def __init__(self, source: str) -> None:
        self.source = source

    def generate(self, request: ModelRequest) -> ProviderResponse:
        del request
        return ProviderResponse(
            request_id="reference-fixture",
            content=self.source,
            reasoning_content="",
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                reasoning_tokens=0,
            ),
            raw_events=({"request_id": "reference-fixture", "output": {}},),
        )


class UnavailableSandbox(UnsafeLocalSandbox):
    def ensure_available(self) -> None:
        raise HarnessUnavailable("simulated Docker launch failure")


def _prepared_manifest(tmp_path: Path) -> tuple[Path, GenerationManifest]:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "stage0"
    manifest = prepare_stage0_run(config, root, run_directory, "scoring-test")
    return run_directory / "manifest.json", manifest


def _passing_outcomes(manifest: GenerationManifest) -> tuple[JobOutcome, ...]:
    outcomes: list[JobOutcome] = []
    for job in manifest.jobs:
        policy_a = (
            RawOutcome.PASS
            if job.assigned_policy is PolicyValue.A
            else RawOutcome.FAIL
        )
        policy_b = (
            RawOutcome.PASS
            if job.assigned_policy is PolicyValue.B
            else RawOutcome.FAIL
        )
        if job.condition is Stage0Condition.ORIGINAL_BENCHMARK:
            policy_a = RawOutcome.NOT_APPLICABLE
            policy_b = RawOutcome.NOT_APPLICABLE
        outcomes.append(
            JobOutcome(
                job_id=job.job_id,
                task_id=job.task_id,
                condition=job.condition,
                assigned_policy=job.assigned_policy,
                sample_index=job.sample_index,
                generation_status=GenerationStatus.GENERATED,
                compilation=RawOutcome.PASS,
                functionality=RawOutcome.PASS,
                policy_a=policy_a,
                policy_b=policy_b,
                original_security=RawOutcome.PASS,
            )
        )
    return tuple(outcomes)


def test_complete_passing_matrix_requires_manual_dataset_review(
    tmp_path: Path,
) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)

    report = score_outcomes(manifest, _passing_outcomes(manifest))
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.complete
    assert len(report.manifest_sha256) == 64
    assert report.automatic_gates_passed
    assert report.recommendation is OverallRecommendation.MANUAL_REVIEW_REQUIRED
    assert report.derived.relevant_assigned_policy_given_functional_rate == 1.0
    assert report.derived.full_policy_controllability == 1.0
    assert report.derived.mutual_exclusivity_violation_count == 0
    assert all(
        gates[gate_id].status is GateStatus.PASSED
        for gate_id in ("G1", "G1b", "G2", "G3", "G4", "G5", "G6", "G8")
    )
    assert gates["G7"].status is GateStatus.MANUAL_REVIEW


def test_passing_dataset_audit_allows_continue_to_stage1(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    dataset_audit = build_dataset_audit_review(
        reviewer="dataset-reviewer",
        unambiguous_applicable_clauses=True,
        distractors_genuinely_irrelevant=True,
        notes="Reviewed all five A/B document pairs.",
    )

    report = score_outcomes(
        manifest,
        _passing_outcomes(manifest),
        dataset_audit=dataset_audit,
    )

    assert report.dataset_audit.status is DatasetAuditStatus.PASSED
    assert report.recommendation is OverallRecommendation.CONTINUE_TO_STAGE1
    assert not report.manual_review_required
    assert {gate.gate_id: gate for gate in report.gates}["G7"].status is GateStatus.PASSED


def test_failed_dataset_audit_invalidates_task_matrix(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    dataset_audit = build_dataset_audit_review(
        reviewer="dataset-reviewer",
        unambiguous_applicable_clauses=True,
        distractors_genuinely_irrelevant=False,
        notes="One distractor can affect the requested API.",
    )

    report = score_outcomes(
        manifest,
        _passing_outcomes(manifest),
        dataset_audit=dataset_audit,
    )

    assert report.dataset_audit.status is DatasetAuditStatus.FAILED
    assert report.recommendation is OverallRecommendation.INVALID_TASK_OR_TESTS
    assert {gate.gate_id: gate for gate in report.gates}["G7"].status is GateStatus.INVALID


def test_partial_dataset_audit_is_rejected() -> None:
    with pytest.raises(ScoringError, match="requires a reviewer and explicit results"):
        build_dataset_audit_review(
            reviewer="dataset-reviewer",
            unambiguous_applicable_clauses=True,
        )


def test_failed_full_document_headroom_returns_stop_or_pivot(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = tuple(
        outcome.model_copy(
            update={"policy_a": RawOutcome.FAIL, "policy_b": RawOutcome.FAIL}
        )
        if outcome.condition
        in {
            Stage0Condition.FULL_DOCUMENT_A,
            Stage0Condition.FULL_DOCUMENT_B,
        }
        else outcome
        for outcome in _passing_outcomes(manifest)
    )

    report = score_outcomes(manifest, outcomes)
    gates = {gate.gate_id: gate for gate in report.gates}

    assert not report.automatic_gates_passed
    assert report.recommendation is OverallRecommendation.STOP_OR_PIVOT
    assert gates["G3"].status is GateStatus.FAILED
    assert gates["G4"].status is GateStatus.FAILED
    assert gates["G5"].status is GateStatus.FAILED


def test_full_document_functionality_gate_uses_all_full_outputs(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    full_conditions = {
        Stage0Condition.FULL_DOCUMENT_A,
        Stage0Condition.FULL_DOCUMENT_B,
    }
    outcomes = tuple(
        outcome.model_copy(update={"functionality": RawOutcome.FAIL})
        if outcome.condition in full_conditions
        else outcome
        for outcome in _passing_outcomes(manifest)
    )

    report = score_outcomes(manifest, outcomes)
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.derived.full_functional_rate == 0.0
    assert gates["G1b"].status is GateStatus.FAILED
    assert report.recommendation is OverallRecommendation.STOP_OR_PIVOT


def test_g5_counts_nonfunctional_completed_pairs_as_failures(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    first_task = manifest.jobs[0].task_id
    full_conditions = {
        Stage0Condition.FULL_DOCUMENT_A,
        Stage0Condition.FULL_DOCUMENT_B,
    }
    outcomes = tuple(
        outcome.model_copy(update={"functionality": RawOutcome.FAIL})
        if outcome.condition in full_conditions and outcome.task_id != first_task
        else outcome
        for outcome in _passing_outcomes(manifest)
    )

    report = score_outcomes(manifest, outcomes)
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.derived.full_policy_controllability == 0.2
    assert gates["G5"].status is GateStatus.PASSED
    assert gates["G1b"].status is GateStatus.FAILED


def test_any_functional_both_policy_pass_invalidates_tasks_or_tests(
    tmp_path: Path,
) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = list(_passing_outcomes(manifest))
    index = next(
        index
        for index, outcome in enumerate(outcomes)
        if outcome.condition is Stage0Condition.SURFACE_ONLY_DIRECT
    )
    outcomes[index] = outcomes[index].model_copy(
        update={"policy_a": RawOutcome.PASS, "policy_b": RawOutcome.PASS}
    )

    report = score_outcomes(manifest, tuple(outcomes))
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.derived.mutual_exclusivity_violation_count == 1
    assert gates["G6"].status is GateStatus.INVALID
    assert report.recommendation is OverallRecommendation.INVALID_TASK_OR_TESTS


def test_policy_compliance_gate_cannot_be_satisfied_by_nonfunctional_outputs(
    tmp_path: Path,
) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    relevant_conditions = {
        Stage0Condition.RELEVANT_CLAUSE_ONLY_A,
        Stage0Condition.RELEVANT_CLAUSE_ONLY_B,
    }
    relevant_index = 0
    outcomes: list[JobOutcome] = []
    for outcome in _passing_outcomes(manifest):
        if outcome.condition not in relevant_conditions:
            outcomes.append(outcome)
            continue
        functional = RawOutcome.PASS if relevant_index < 4 else RawOutcome.FAIL
        relevant_index += 1
        outcomes.append(
            outcome.model_copy(
                update={
                    "functionality": functional,
                    "policy_a": (
                        RawOutcome.FAIL
                        if functional is RawOutcome.PASS
                        else outcome.policy_a
                    ),
                    "policy_b": (
                        RawOutcome.FAIL
                        if functional is RawOutcome.PASS
                        else outcome.policy_b
                    ),
                }
            )
        )

    report = score_outcomes(manifest, tuple(outcomes))
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.derived.relevant_functional_rate == 0.4
    assert report.derived.relevant_assigned_policy_given_functional_rate == 0.0
    assert gates["G1"].status is GateStatus.PASSED
    assert gates["G2"].status is GateStatus.FAILED


def test_incomplete_matrix_is_never_a_continue_decision(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)

    report = score_outcomes(manifest, _passing_outcomes(manifest)[:-1])

    assert not report.complete
    assert report.recommendation is OverallRecommendation.INCOMPLETE
    assert report.missing_jobs == (manifest.jobs[-1].job_id,)


def test_incomplete_precedes_invalid_task_state(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = list(_passing_outcomes(manifest)[:-1])
    index = next(
        index
        for index, outcome in enumerate(outcomes)
        if outcome.condition is Stage0Condition.SURFACE_ONLY_DIRECT
    )
    outcomes[index] = outcomes[index].model_copy(
        update={"policy_a": RawOutcome.PASS, "policy_b": RawOutcome.PASS}
    )

    report = score_outcomes(manifest, tuple(outcomes))

    assert report.recommendation is OverallRecommendation.INCOMPLETE


def test_scoring_rejects_duplicate_job_outcomes(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = _passing_outcomes(manifest)

    with pytest.raises(ScoringError, match="duplicate job IDs"):
        score_outcomes(manifest, (*outcomes, outcomes[0]))


def test_evaluator_persists_provenance_bound_suite_results(tmp_path: Path) -> None:
    root = Path.cwd()
    manifest_path, manifest = _prepared_manifest(tmp_path)
    source = (root / "tasks/path_symlink_report/original_reference.py").read_text(
        encoding="utf-8"
    )
    run_stage0_generation(
        manifest_path,
        ReferenceGenerationClient(source),
        limit=1,
    )

    summary = evaluate_generated_candidates(
        manifest_path,
        root,
        UnsafeLocalSandbox(manifest.sandbox),
        limit=1,
    )

    assert summary.evaluated == 1
    assert summary.unselected_jobs == 39
    evaluation_path = (
        manifest_path.parent / "jobs" / manifest.jobs[0].job_id / "evaluation.json"
    )
    artifact = EvaluationArtifact.model_validate_json(evaluation_path.read_text(encoding="utf-8"))
    assert len(artifact.manifest_sha256) == 64
    assert artifact.evaluation is not None
    assert artifact.evaluation.compile.status is RunStatus.PASSED
    assert artifact.evaluation.suites[SuiteKind.FUNCTIONALITY].status is RunStatus.PASSED
    assert artifact.evaluation.suites[SuiteKind.POLICY_A].status is RunStatus.SKIPPED
    assert artifact.evaluation.suites[SuiteKind.POLICY_B].status is RunStatus.SKIPPED
    assert artifact.evaluation.suites[SuiteKind.ORIGINAL_SECURITY].status is RunStatus.PASSED

    report = build_stage0_report(manifest_path)
    outcome = report.outcomes[0]
    assert outcome.compilation is RawOutcome.PASS
    assert outcome.functionality is RawOutcome.PASS
    assert outcome.policy_a is RawOutcome.NOT_APPLICABLE
    assert outcome.policy_b is RawOutcome.NOT_APPLICABLE
    assert outcome.original_security is RawOutcome.PASS
    assert report.condition_metrics[Stage0Condition.ORIGINAL_BENCHMARK].policy_a_rate is None
    assert "N/A" in render_markdown(report)


def test_compile_failure_retains_not_run_suite_outcomes(tmp_path: Path) -> None:
    root = Path.cwd()
    manifest_path, manifest = _prepared_manifest(tmp_path)
    run_stage0_generation(
        manifest_path,
        ReferenceGenerationClient("def broken(:"),
        limit=1,
    )
    evaluate_generated_candidates(
        manifest_path,
        root,
        UnsafeLocalSandbox(manifest.sandbox),
        limit=1,
    )

    outcome = build_stage0_report(manifest_path).outcomes[0]
    assert outcome.compilation is RawOutcome.FAIL
    assert outcome.functionality is RawOutcome.NOT_RUN
    assert outcome.policy_a is RawOutcome.NOT_APPLICABLE
    assert outcome.policy_b is RawOutcome.NOT_APPLICABLE
    assert outcome.original_security is RawOutcome.NOT_RUN


def test_evaluator_rejects_a_changed_raw_provider_response(tmp_path: Path) -> None:
    root = Path.cwd()
    manifest_path, manifest = _prepared_manifest(tmp_path)
    source = (root / "tasks/path_symlink_report/original_reference.py").read_text(
        encoding="utf-8"
    )
    run_stage0_generation(
        manifest_path,
        ReferenceGenerationClient(source),
        limit=1,
    )
    response_path = (
        manifest_path.parent
        / "jobs"
        / manifest.jobs[0].job_id
        / "responses/response-01.json"
    )
    response_path.write_text(
        f"{response_path.read_text(encoding='utf-8')}\n",
        encoding="utf-8",
    )

    with pytest.raises(ScoringError, match="raw response changed after generation"):
        evaluate_generated_candidates(
            manifest_path,
            root,
            UnsafeLocalSandbox(manifest.sandbox),
            limit=1,
        )


def test_infrastructure_failure_leaves_job_incomplete_and_retryable(tmp_path: Path) -> None:
    root = Path.cwd()
    manifest_path, manifest = _prepared_manifest(tmp_path)
    source = (root / "tasks/path_symlink_report/original_reference.py").read_text(
        encoding="utf-8"
    )
    run_stage0_generation(
        manifest_path,
        ReferenceGenerationClient(source),
        limit=1,
    )

    with pytest.raises(HarnessUnavailable, match="simulated Docker launch failure"):
        evaluate_generated_candidates(
            manifest_path,
            root,
            UnavailableSandbox(manifest.sandbox),
            limit=1,
        )

    evaluation_path = (
        manifest_path.parent / "jobs" / manifest.jobs[0].job_id / "evaluation.json"
    )
    assert not evaluation_path.exists()
    report = build_stage0_report(manifest_path)
    assert report.recommendation is OverallRecommendation.INCOMPLETE
    assert manifest.jobs[0].job_id in report.missing_jobs


def test_report_is_human_readable_and_immutable(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    report = score_outcomes(manifest, _passing_outcomes(manifest))
    output_directory = tmp_path / "report"

    write_stage0_report(report, output_directory)
    markdown = render_markdown(report)

    assert "five-task smoke test, not statistical findings" in markdown
    assert "G7: Dataset applicability and distractor integrity" in markdown
    assert (output_directory / "stage0-report.json").is_file()
    assert (output_directory / "stage0-report.md").is_file()
    with pytest.raises(ScoringError, match="not empty"):
        write_stage0_report(report, output_directory)
