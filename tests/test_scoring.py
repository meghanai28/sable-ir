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
from sable_ir.harness import RunStatus, UnsafeLocalSandbox
from sable_ir.provider import ModelRequest, ProviderResponse, TokenUsage
from sable_ir.schema import PolicyValue, Stage0Condition
from sable_ir.schema import TestSuiteKind as SuiteKind
from sable_ir.scoring import (
    EvaluationArtifact,
    GateStatus,
    JobOutcome,
    OverallRecommendation,
    ScoringError,
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


def _prepared_manifest(tmp_path: Path) -> tuple[Path, GenerationManifest]:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "stage0"
    manifest = prepare_stage0_run(config, root, run_directory, "scoring-test")
    return run_directory / "manifest.json", manifest


def _passing_outcomes(manifest: GenerationManifest) -> tuple[JobOutcome, ...]:
    outcomes: list[JobOutcome] = []
    for job in manifest.jobs:
        policy_a = job.assigned_policy is PolicyValue.A
        policy_b = job.assigned_policy is PolicyValue.B
        if job.assigned_policy is None:
            policy_a = False
            policy_b = False
        outcomes.append(
            JobOutcome(
                job_id=job.job_id,
                task_id=job.task_id,
                condition=job.condition,
                assigned_policy=job.assigned_policy,
                sample_index=job.sample_index,
                generation_status=GenerationStatus.GENERATED,
                compiled=True,
                functionality=True,
                policy_a=policy_a,
                policy_b=policy_b,
                original_security=True,
            )
        )
    return tuple(outcomes)


def test_complete_passing_matrix_requires_manual_clause_selection_review(
    tmp_path: Path,
) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)

    report = score_outcomes(manifest, _passing_outcomes(manifest))
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.complete
    assert len(report.manifest_sha256) == 64
    assert report.automatic_gates_passed
    assert report.recommendation is OverallRecommendation.MANUAL_REVIEW_REQUIRED
    assert report.derived.relevant_assigned_policy_rate == 1.0
    assert report.derived.full_policy_controllability == 1.0
    assert report.derived.surface_both_policies_rate == 0.0
    assert all(gates[f"G{index}"].status is GateStatus.PASSED for index in (1, 2, 3, 4, 5, 6, 8))
    assert gates["G7"].status is GateStatus.MANUAL_REVIEW


def test_failed_full_document_headroom_returns_stop_or_pivot(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = tuple(
        outcome.model_copy(update={"policy_a": False, "policy_b": False})
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


def test_incomplete_matrix_is_never_a_continue_decision(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)

    report = score_outcomes(manifest, _passing_outcomes(manifest)[:-1])

    assert not report.complete
    assert report.recommendation is OverallRecommendation.INCOMPLETE
    assert report.missing_jobs == (manifest.jobs[-1].job_id,)


def test_scoring_rejects_duplicate_job_outcomes(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    outcomes = _passing_outcomes(manifest)

    with pytest.raises(ScoringError, match="duplicate job IDs"):
        score_outcomes(manifest, (*outcomes, outcomes[0]))


def test_evaluator_persists_provenance_bound_suite_results(tmp_path: Path) -> None:
    root = Path.cwd()
    manifest_path, manifest = _prepared_manifest(tmp_path)
    source = (root / "tasks/path_symlink_report/reference_a.py").read_text(encoding="utf-8")
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
    assert artifact.evaluation.suites[SuiteKind.POLICY_A].status is RunStatus.PASSED
    assert artifact.evaluation.suites[SuiteKind.POLICY_B].status is RunStatus.FAILED
    assert artifact.evaluation.suites[SuiteKind.ORIGINAL_SECURITY].status is RunStatus.PASSED


def test_report_is_human_readable_and_immutable(tmp_path: Path) -> None:
    _manifest_path, manifest = _prepared_manifest(tmp_path)
    report = score_outcomes(manifest, _passing_outcomes(manifest))
    output_directory = tmp_path / "report"

    write_stage0_report(report, output_directory)
    markdown = render_markdown(report)

    assert "five-task smoke test, not statistical findings" in markdown
    assert "G7: Visible full-plan applicable-clause selection" in markdown
    assert (output_directory / "stage0-report.json").is_file()
    assert (output_directory / "stage0-report.md").is_file()
    with pytest.raises(ScoringError, match="not empty"):
        write_stage0_report(report, output_directory)
