"""Small validation CLI; experiment commands are added at later checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from sable_ir.audit import audit_stage0_tasks
from sable_ir.config import ConfigLoadError, load_stage0_config, load_task
from sable_ir.generation import (
    GenerationError,
    GenerationManifest,
    GenerationRecord,
    GenerationStatus,
    client_from_environment,
    load_manifest,
    prepare_stage0_dataset_revision,
    prepare_stage0_recovery,
    prepare_stage0_run,
    provider_preflight,
    run_stage0_generation,
    select_manifest_jobs,
)
from sable_ir.harness import (
    DockerSandbox,
    EvaluationHarness,
    HarnessError,
    UnsafeLocalSandbox,
)
from sable_ir.schema import (
    Stage0Condition,
    Stage0Config,
    TaskSpec,
    TestSuiteKind,
    json_schema_for,
)
from sable_ir.scoring import (
    EvaluationArtifact,
    OverallRecommendation,
    ScoringError,
    build_dataset_audit_review,
    build_stage0_report,
    evaluate_generated_candidates,
    write_stage0_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sable-ir")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("validate-config", help="validate Stage 0 TOML")
    config_parser.add_argument("path", type=Path)

    task_parser = subparsers.add_parser("validate-task", help="validate task JSON")
    task_parser.add_argument("paths", type=Path, nargs="+")

    schema_parser = subparsers.add_parser("print-schema", help="print a JSON Schema")
    schema_parser.add_argument("kind", choices=("stage0-config", "task"))

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="compile a candidate and run all four task suites"
    )
    evaluate_parser.add_argument("task", type=Path)
    evaluate_parser.add_argument("candidate", type=Path)
    evaluate_parser.add_argument("--config", type=Path, default=Path("config/stage0.toml"))
    evaluate_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    evaluate_parser.add_argument("--output", type=Path)
    evaluate_parser.add_argument(
        "--unsafe-local",
        action="store_true",
        help="run trusted fixtures on the host without a security boundary",
    )

    audit_parser = subparsers.add_parser(
        "audit-tasks", help="validate task assets and the A/B reference test matrix"
    )
    audit_parser.add_argument("--config", type=Path, default=Path("config/stage0.toml"))
    audit_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    audit_parser.add_argument("--output", type=Path)
    audit_parser.add_argument(
        "--unsafe-local",
        action="store_true",
        help="audit trusted references on the host when Docker is unavailable",
    )

    preflight_parser = subparsers.add_parser(
        "kimi-preflight", help="check local hosted-Kimi configuration without an API call"
    )
    preflight_parser.add_argument("--config", type=Path, default=Path("config/stage0.toml"))

    prepare_parser = subparsers.add_parser(
        "prepare-stage0", help="freeze the Stage 0 request matrix without calling Kimi"
    )
    prepare_parser.add_argument("--run-id", required=True)
    prepare_parser.add_argument("--config", type=Path, default=Path("config/stage0.toml"))
    prepare_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    prepare_parser.add_argument("--run-directory", type=Path)
    prepare_parser.add_argument(
        "--migrated-from-manifest-sha256",
        help="record the prior manifest hash for a metadata-only artifact migration",
    )
    prepare_parser.add_argument(
        "--recovery-from-manifest",
        type=Path,
        help="create a lineage-linked manual recovery from an interrupted run",
    )
    prepare_parser.add_argument(
        "--authorize-retry-job-id",
        help="authorize one new-run attempt for the source run's retryable 429 job",
    )
    prepare_parser.add_argument(
        "--retry-cooldown-seconds",
        type=int,
        default=65,
        help="frozen cooldown: 65 for a 429 recovery, 0 for a stream timeout",
    )
    prepare_parser.add_argument(
        "--retry-reason",
        choices=("provider_rate_limit_429", "stream_timeout_600"),
        default="provider_rate_limit_429",
    )
    prepare_parser.add_argument(
        "--execution-job-id",
        action="append",
        default=[],
        help="freeze recovery execution order; repeat once per pending job",
    )
    prepare_parser.add_argument(
        "--revision-from-manifest",
        type=Path,
        help="carry exact-input results from a completed pre-revision run",
    )
    prepare_parser.add_argument(
        "--g7-audit",
        type=Path,
        help="completed passing G7 audit for the revised task bundle",
    )
    prepare_parser.add_argument(
        "--changed-task-id",
        action="append",
        default=[],
        help="task whose full-document prompts must be invalidated; repeat as needed",
    )

    generate_parser = subparsers.add_parser(
        "generate-stage0", help="execute or inspect a prepared, resumable Kimi run"
    )
    generate_parser.add_argument("manifest", type=Path)
    generation_selection = generate_parser.add_mutually_exclusive_group()
    generation_selection.add_argument("--job-id")
    generation_selection.add_argument(
        "--all", action="store_true", help="select the full run after both canaries are audited"
    )
    generate_parser.add_argument(
        "--confirm-full-run",
        metavar="RUN_ID",
        help="required with --all for live generation; must exactly match the manifest run ID",
    )
    generate_parser.add_argument(
        "--dry-run", action="store_true", help="show run status without credentials or API calls"
    )

    score_parser = subparsers.add_parser(
        "evaluate-stage0", help="sandbox and score generated candidates from a frozen run"
    )
    score_parser.add_argument("manifest", type=Path)
    score_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    score_selection = score_parser.add_mutually_exclusive_group()
    score_selection.add_argument("--limit", type=int)
    score_selection.add_argument("--job-id")
    score_parser.add_argument(
        "--unsafe-local",
        action="store_true",
        help="score only trusted fixtures on the host without a security boundary",
    )

    report_parser = subparsers.add_parser(
        "report-stage0", help="aggregate immutable evaluations and apply Stage 0 gates"
    )
    report_parser.add_argument("manifest", type=Path)
    report_parser.add_argument("--report-id", required=True)
    report_parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="write a clearly marked partial report before every job is evaluated",
    )
    report_parser.add_argument(
        "--dataset-audit-reviewer",
        help="name recorded with a completed manual safety-document audit",
    )
    report_parser.add_argument(
        "--applicable-clause-audit",
        choices=("passed", "failed"),
        help="manual result: every document has one unambiguous applicable clause",
    )
    report_parser.add_argument(
        "--distractor-audit",
        choices=("passed", "failed"),
        help="manual result: every distractor clause is genuinely irrelevant",
    )
    report_parser.add_argument("--dataset-audit-notes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            config = load_stage0_config(args.path)
            print(
                f"valid Stage 0 config: {len(config.task_paths)} tasks, "
                f"{len(config.conditions)} conditions, model {config.hosted_kimi.model}"
            )
        elif args.command == "validate-task":
            for path in args.paths:
                task = load_task(path)
                print(f"valid task: {task.id}")
        elif args.command == "print-schema":
            model = Stage0Config if args.kind == "stage0-config" else TaskSpec
            print(json.dumps(json_schema_for(model), indent=2, sort_keys=True))
        elif args.command == "evaluate":
            config = load_stage0_config(args.config)
            task = load_task(args.task)
            backend = (
                UnsafeLocalSandbox(config.sandbox)
                if args.unsafe_local
                else DockerSandbox(config.sandbox)
            )
            evaluation_result = EvaluationHarness(args.repository_root, backend).evaluate(
                task, args.candidate
            )
            serialized = evaluation_result.model_dump_json(indent=2)
            if args.output is None:
                print(serialized)
            else:
                args.output.write_text(f"{serialized}\n", encoding="utf-8")
                print(f"wrote evaluation: {args.output}")
        elif args.command == "audit-tasks":
            config = load_stage0_config(args.config)
            backend = (
                UnsafeLocalSandbox(config.sandbox)
                if args.unsafe_local
                else DockerSandbox(config.sandbox)
            )
            audit_result = audit_stage0_tasks(config, args.repository_root, backend)
            serialized = audit_result.model_dump_json(indent=2)
            if args.output is None:
                print(serialized)
            else:
                args.output.write_text(f"{serialized}\n", encoding="utf-8")
                print(f"wrote task audit: {args.output}")
            if not audit_result.passed:
                return 1
        elif args.command == "kimi-preflight":
            config = load_stage0_config(args.config)
            preflight = provider_preflight(config.hosted_kimi)
            print(preflight.model_dump_json(indent=2))
            if not preflight.ready_for_requests:
                return 1
        elif args.command == "prepare-stage0":
            config = load_stage0_config(args.config)
            run_directory = args.run_directory or (
                args.repository_root / config.artifacts_dir / "stage0" / args.run_id
            )
            recovery_requested = args.recovery_from_manifest is not None
            retry_job_provided = args.authorize_retry_job_id is not None
            if recovery_requested != retry_job_provided:
                raise GenerationError(
                    "recovery requires both --recovery-from-manifest and "
                    "--authorize-retry-job-id"
                )
            revision_fields = (
                args.revision_from_manifest is not None,
                args.g7_audit is not None,
                bool(args.changed_task_id),
            )
            if any(revision_fields) and not all(revision_fields):
                raise GenerationError(
                    "dataset revision requires --revision-from-manifest, --g7-audit, "
                    "and at least one --changed-task-id"
                )
            revision_requested = all(revision_fields)
            if recovery_requested and revision_requested:
                raise GenerationError("rate-limit recovery and dataset revision are separate runs")
            if args.execution_job_id and not recovery_requested:
                raise GenerationError("--execution-job-id is only valid for a recovery run")
            if (
                recovery_requested or revision_requested
            ) and args.migrated_from_manifest_sha256 is not None:
                raise GenerationError(
                    "lineage preparation computes its source manifest hash automatically"
                )
            if revision_requested:
                manifest = prepare_stage0_dataset_revision(
                    config,
                    args.repository_root,
                    args.revision_from_manifest,
                    args.g7_audit,
                    run_directory,
                    args.run_id,
                    tuple(args.changed_task_id),
                )
            elif recovery_requested:
                manifest = prepare_stage0_recovery(
                    config,
                    args.repository_root,
                    args.recovery_from_manifest,
                    run_directory,
                    args.run_id,
                    args.authorize_retry_job_id,
                    cooldown_seconds=args.retry_cooldown_seconds,
                    retry_reason=args.retry_reason,
                    execution_order=(
                        tuple(args.execution_job_id) if args.execution_job_id else None
                    ),
                )
            else:
                manifest = prepare_stage0_run(
                    config,
                    args.repository_root,
                    run_directory,
                    args.run_id,
                    args.migrated_from_manifest_sha256,
                )
            print(
                f"prepared {len(manifest.jobs)} immutable requests at "
                f"{run_directory.resolve()}"
            )
        elif args.command == "generate-stage0":
            manifest = load_manifest(args.manifest)
            if args.dry_run:
                run_directory = args.manifest.resolve().parent
                completed = sum(
                    (run_directory / job.result_path).exists() for job in manifest.jobs
                )
                selected = select_manifest_jobs(
                    manifest,
                    job_id=args.job_id,
                    use_execution_order=True,
                )
                print(
                    f"dry run: {manifest.run_id}, {len(manifest.jobs)} total jobs, "
                    f"{completed} complete, {len(selected)} selected; no API calls made"
                )
            else:
                if args.job_id is None and not args.all:
                    raise GenerationError(
                        "live generation requires one explicit --job-id; use --all only after "
                        "auditing both canaries"
                    )
                if args.all and args.confirm_full_run != manifest.run_id:
                    raise GenerationError(
                        "--all requires --confirm-full-run with the exact manifest run ID"
                    )
                if args.all:
                    _require_canary_artifacts(args.manifest, manifest)
                client = client_from_environment(manifest.provider)
                generation_summary = run_stage0_generation(
                    args.manifest,
                    client,
                    job_id=args.job_id,
                )
                print(generation_summary.model_dump_json(indent=2))
        elif args.command == "evaluate-stage0":
            manifest = load_manifest(args.manifest)
            backend = (
                UnsafeLocalSandbox(manifest.sandbox)
                if args.unsafe_local
                else DockerSandbox(manifest.sandbox)
            )
            evaluation_summary = evaluate_generated_candidates(
                args.manifest,
                args.repository_root,
                backend,
                limit=args.limit,
                job_id=args.job_id,
            )
            print(evaluation_summary.model_dump_json(indent=2))
        elif args.command == "report-stage0":
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", args.report_id):
                raise ScoringError("--report-id must be 1-80 safe filename characters")
            dataset_audit = build_dataset_audit_review(
                reviewer=args.dataset_audit_reviewer,
                unambiguous_applicable_clauses=_audit_choice(
                    args.applicable_clause_audit
                ),
                distractors_genuinely_irrelevant=_audit_choice(args.distractor_audit),
                notes=args.dataset_audit_notes,
            )
            report = build_stage0_report(args.manifest, dataset_audit)
            if not report.complete and not args.allow_incomplete:
                raise ScoringError(
                    f"report is incomplete ({report.scored_jobs}/{report.expected_jobs}); "
                    "finish evaluation or pass --allow-incomplete"
                )
            output_directory = (
                args.manifest.resolve().parent / "reports" / args.report_id
            )
            write_stage0_report(report, output_directory)
            print(
                f"wrote Stage 0 report to {output_directory}: "
                f"{report.recommendation.value}"
            )
            if report.recommendation in {
                OverallRecommendation.INCOMPLETE,
                OverallRecommendation.INVALID_TASK_OR_TESTS,
                OverallRecommendation.STOP_OR_PIVOT,
            }:
                return 1
    except (ConfigLoadError, GenerationError, HarnessError, ScoringError) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


def _audit_choice(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "passed"


def _require_canary_artifacts(
    manifest_path: Path, manifest: GenerationManifest
) -> None:
    """Refuse a paid full run until both canaries generated and were evaluated."""
    first_task_id = manifest.jobs[0].task_id
    required_conditions = (
        Stage0Condition.ORIGINAL_BENCHMARK,
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A,
    )
    run_directory = manifest_path.resolve().parent
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    for condition in required_conditions:
        matching = [
            job
            for job in manifest.jobs
            if job.task_id == first_task_id
            and job.condition is condition
            and job.sample_index == 0
        ]
        if len(matching) != 1:
            raise GenerationError(
                f"manifest must contain one {condition.value} canary for {first_task_id}"
            )
        job = matching[0]
        result_path = run_directory / job.result_path
        evaluation_path = run_directory / "jobs" / job.job_id / "evaluation.json"
        missing = [
            str(path.relative_to(run_directory))
            for path in (result_path, evaluation_path)
            if not path.is_file()
        ]
        if missing:
            raise GenerationError(
                "full generation is locked until both canaries have result.json and "
                f"evaluation.json artifacts; missing: {', '.join(missing)}"
            )
        try:
            result_bytes = result_path.read_bytes()
            generation = GenerationRecord.model_validate_json(result_bytes)
            evaluation = EvaluationArtifact.model_validate_json(
                evaluation_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as error:
            raise GenerationError(
                f"full generation is locked: could not validate canary {job.job_id}: {error}"
            ) from error

        generation_identity = (
            generation.job_id,
            generation.task_id,
            generation.condition,
            generation.assigned_policy,
            generation.sample_index,
            generation.pair_id,
            generation.model,
            generation.thinking_requested,
        )
        job_identity = (
            job.job_id,
            job.task_id,
            job.condition,
            job.assigned_policy,
            job.sample_index,
            job.pair_id,
            manifest.provider.model,
            job.thinking_requested,
        )
        if generation_identity != job_identity:
            raise GenerationError(
                f"full generation is locked: canary metadata mismatch for {job.job_id}"
            )
        if (
            generation.status is not GenerationStatus.GENERATED
            or generation.finish_reason == "length"
            or generation.candidate_path is None
            or generation.candidate_sha256 is None
        ):
            raise GenerationError(
                "full generation is locked: canary did not complete with runnable output: "
                f"{job.job_id} ({generation.status.value}, "
                f"finish_reason={generation.finish_reason!r})"
            )
        if condition is Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A and (
            generation.thinking_requested != "enabled"
            or not generation.reasoning_content_present
        ):
            raise GenerationError(
                f"full generation is locked: thinking evidence is missing for {job.job_id}"
            )

        candidate_path = _checked_canary_path(
            run_directory, generation.candidate_path, "candidate"
        )
        raw_response_path = _checked_canary_path(
            run_directory, generation.raw_response_path, "raw response"
        )
        try:
            candidate_sha256 = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
            raw_response_sha256 = hashlib.sha256(raw_response_path.read_bytes()).hexdigest()
        except OSError as error:
            raise GenerationError(
                f"full generation is locked: could not read canary artifact: {error}"
            ) from error
        if candidate_sha256 != generation.candidate_sha256:
            raise GenerationError(
                f"full generation is locked: candidate hash mismatch for {job.job_id}"
            )
        if raw_response_sha256 != generation.raw_response_sha256:
            raise GenerationError(
                f"full generation is locked: raw response hash mismatch for {job.job_id}"
            )
        if condition is Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A:
            if generation.reasoning_path is None or generation.reasoning_sha256 is None:
                raise GenerationError(
                    f"full generation is locked: reasoning artifact is missing for {job.job_id}"
                )
            reasoning_path = _checked_canary_path(
                run_directory, generation.reasoning_path, "reasoning"
            )
            try:
                reasoning_sha256 = hashlib.sha256(reasoning_path.read_bytes()).hexdigest()
            except OSError as error:
                raise GenerationError(
                    f"full generation is locked: could not read reasoning artifact: {error}"
                ) from error
            if reasoning_sha256 != generation.reasoning_sha256:
                raise GenerationError(
                    f"full generation is locked: reasoning hash mismatch for {job.job_id}"
                )

        expected_result_sha256 = hashlib.sha256(result_bytes).hexdigest()
        if (
            evaluation.job_id != job.job_id
            or evaluation.harness_version != manifest.evaluation_harness_version
            or evaluation.manifest_sha256 != manifest_sha256
            or evaluation.generation_result_sha256 != expected_result_sha256
            or evaluation.candidate_path != generation.candidate_path
            or evaluation.evaluation is None
        ):
            raise GenerationError(
                f"full generation is locked: evaluation provenance is invalid for {job.job_id}"
            )
        evaluated = evaluation.evaluation
        if (
            evaluated.task_id != job.task_id
            or evaluated.candidate_sha256 != generation.candidate_sha256
            or evaluated.backend != manifest.sandbox.backend
            or set(evaluated.suites) != set(TestSuiteKind)
        ):
            raise GenerationError(
                f"full generation is locked: evaluation is incomplete for {job.job_id}"
            )


def _checked_canary_path(run_directory: Path, relative: str, label: str) -> Path:
    path = (run_directory / relative).resolve()
    if not path.is_relative_to(run_directory):
        raise GenerationError(f"full generation is locked: unsafe {label} path")
    if not path.is_file():
        raise GenerationError(f"full generation is locked: missing {label} artifact")
    return path
