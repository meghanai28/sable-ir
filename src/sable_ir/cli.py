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
from sable_ir.config import ConfigLoadError, load_stage0_config, load_stage1_config, load_task
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
from sable_ir.stage1 import (
    Stage1Error,
    build_stage1a_status,
    evaluate_stage1_renders,
    load_plan_manifest,
    load_render_manifest,
    prepare_stage1_plan_recovery,
    prepare_stage1_plans,
    prepare_stage1_renders,
    require_plan_canary,
    require_render_canary,
    run_stage1_plans,
    run_stage1_renders,
)
from sable_ir.stage1 import (
    client_from_environment as stage1_client_from_environment,
)
from sable_ir.stage1_analysis import (
    build_behavioral_metrics,
    build_length_report,
    fetch_kimi_tokenizer,
    prepare_plan_audit,
    summarize_plan_audit,
)
from sable_ir.stage1_controls import (
    ControlPlanKind,
    RendererControlKind,
    SurfaceBaselineManifest,
    evaluate_surface_baseline,
    prepare_control_plan_audit,
    prepare_control_plans,
    prepare_renderer_control,
    prepare_surface_baseline,
    report_surface_baseline,
    require_control_plan_canary,
    require_surface_baseline_canary,
    run_control_plans,
    run_surface_baseline,
    validate_control_plan_audit,
)
from sable_ir.stage1_report import Stage1Recommendation, build_stage1_report
from sable_ir.stage2 import Stage2Error
from sable_ir.stage2_cli import add_stage2_parsers, handle_stage2_command
from sable_ir.stage3 import Stage3Error
from sable_ir.stage3_cli import add_stage3_parsers, handle_stage3_command
from sable_ir.stage4 import Stage4Error
from sable_ir.stage4_cli import add_stage4_parsers, handle_stage4_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sable-ir")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("validate-config", help="validate Stage 0 TOML")
    config_parser.add_argument("path", type=Path)

    stage1_config_parser = subparsers.add_parser(
        "validate-stage1-config", help="validate Stage 1A TOML"
    )
    stage1_config_parser.add_argument("path", type=Path)

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

    stage1_preflight_parser = subparsers.add_parser(
        "stage1-kimi-preflight",
        help="check local Stage 1A hosted-Kimi configuration without an API call",
    )
    stage1_preflight_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))

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

    prepare_plans_parser = subparsers.add_parser(
        "prepare-stage1-plans", help="freeze all Stage 1A planner requests"
    )
    prepare_plans_parser.add_argument("--run-id", required=True)
    prepare_plans_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    prepare_plans_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    prepare_plans_parser.add_argument("--run-directory", type=Path)

    recover_plans_parser = subparsers.add_parser(
        "recover-stage1-plans",
        help="create a lineage-linked continuation after inspected transport/malformed failures",
    )
    recover_plans_parser.add_argument("source_manifest", type=Path)
    recover_plans_parser.add_argument(
        "--retry-job-id",
        action="append",
        required=True,
        help="explicitly authorize one new attempt; repeat once per reviewed failed job",
    )
    recover_plans_parser.add_argument("--run-id", required=True)
    recover_plans_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    recover_plans_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    recover_plans_parser.add_argument("--run-directory", type=Path)

    generate_plans_parser = subparsers.add_parser(
        "generate-stage1-plans", help="run or inspect immutable Stage 1A planner jobs"
    )
    generate_plans_parser.add_argument("manifest", type=Path)
    plan_selection = generate_plans_parser.add_mutually_exclusive_group()
    plan_selection.add_argument("--job-id")
    plan_selection.add_argument("--all", action="store_true")
    generate_plans_parser.add_argument("--confirm-full-run", metavar="RUN_ID")
    generate_plans_parser.add_argument("--dry-run", action="store_true")

    prepare_renders_parser = subparsers.add_parser(
        "prepare-stage1-renders", help="freeze four renderer requests for every exact plan"
    )
    prepare_renders_parser.add_argument("plan_manifest", type=Path)
    prepare_renders_parser.add_argument("--run-id", required=True)
    prepare_renders_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    prepare_renders_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    prepare_renders_parser.add_argument("--run-directory", type=Path)

    generate_renders_parser = subparsers.add_parser(
        "generate-stage1-renders", help="run or inspect immutable Stage 1A renderer jobs"
    )
    generate_renders_parser.add_argument("manifest", type=Path)
    render_selection = generate_renders_parser.add_mutually_exclusive_group()
    render_selection.add_argument("--job-id")
    render_selection.add_argument("--all", action="store_true")
    generate_renders_parser.add_argument("--confirm-full-run", metavar="RUN_ID")
    generate_renders_parser.add_argument("--dry-run", action="store_true")

    evaluate_renders_parser = subparsers.add_parser(
        "evaluate-stage1-renders", help="run all four suites on Stage 1A renderer outputs"
    )
    evaluate_renders_parser.add_argument("manifest", type=Path)
    evaluate_renders_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    evaluate_renders_parser.add_argument("--job-id")
    evaluate_renders_parser.add_argument("--unsafe-local", action="store_true")

    status_parser = subparsers.add_parser(
        "status-stage1a", help="summarize Stage 1A generation and evaluation completeness"
    )
    status_parser.add_argument("plan_manifest", type=Path)
    status_parser.add_argument("--render-manifest", type=Path)
    status_parser.add_argument("--output", type=Path)

    tokenizer_parser = subparsers.add_parser(
        "fetch-stage1-tokenizer", help="fetch and verify the pinned Kimi-K2.6 tokenizer"
    )
    tokenizer_parser.add_argument("output", type=Path)

    length_parser = subparsers.add_parser(
        "analyze-stage1-lengths", help="compute exact Stage 1B lengths and format matches"
    )
    length_parser.add_argument("plan_manifest", type=Path)
    length_parser.add_argument("--tokenizer", type=Path, required=True)
    length_parser.add_argument("--output", type=Path, required=True)

    plan_audit_parser = subparsers.add_parser(
        "prepare-stage1-plan-audit",
        help="write the behavior-blinded Stage 1C plan audit packet",
    )
    plan_audit_parser.add_argument("plan_manifest", type=Path)
    plan_audit_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    plan_audit_parser.add_argument("--output", type=Path, required=True)

    audit_summary_parser = subparsers.add_parser(
        "summarize-stage1-plan-audit", help="validate and summarize a completed plan audit"
    )
    audit_summary_parser.add_argument("audit", type=Path)
    audit_summary_parser.add_argument("plan_manifest", type=Path)

    metrics_parser = subparsers.add_parser(
        "report-stage1-behavior", help="join Stage 1C audit labels with renderer outcomes"
    )
    metrics_parser.add_argument("render_manifest", type=Path)
    metrics_parser.add_argument("plan_manifest", type=Path)
    metrics_parser.add_argument("plan_audit", type=Path)
    metrics_parser.add_argument("surface_baseline", type=Path)
    metrics_parser.add_argument("stage0_report", type=Path)
    metrics_parser.add_argument("--output", type=Path, required=True)

    control_plans_parser = subparsers.add_parser(
        "prepare-stage1-control-plans",
        help="freeze wrong-clause and reversed-clause-order planner controls",
    )
    control_plans_parser.add_argument("plan_manifest", type=Path)
    control_plans_parser.add_argument("--run-id", required=True)
    control_plans_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    control_plans_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    control_plans_parser.add_argument("--run-directory", type=Path, required=True)
    control_plans_parser.add_argument("--tokenizer", type=Path, required=True)

    surface_prepare_parser = subparsers.add_parser(
        "prepare-stage1-surface-baseline",
        help="freeze four policy-neutral Stage 1 renders per task for HU+",
    )
    surface_prepare_parser.add_argument("--run-id", required=True)
    surface_prepare_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    surface_prepare_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    surface_prepare_parser.add_argument("--run-directory", type=Path, required=True)

    surface_run_parser = subparsers.add_parser(
        "generate-stage1-surface-baseline",
        help="execute the repeated Stage 1 surface-only baseline",
    )
    surface_run_parser.add_argument("manifest", type=Path)
    surface_run_selection = surface_run_parser.add_mutually_exclusive_group(required=True)
    surface_run_selection.add_argument("--job-id")
    surface_run_selection.add_argument("--all", action="store_true")
    surface_run_parser.add_argument("--confirm-full-run")

    surface_eval_parser = subparsers.add_parser(
        "evaluate-stage1-surface-baseline", help="evaluate repeated surface-only renders"
    )
    surface_eval_parser.add_argument("manifest", type=Path)
    surface_eval_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    surface_eval_parser.add_argument("--job-id")
    surface_eval_parser.add_argument("--unsafe-local", action="store_true")

    surface_report_parser = subparsers.add_parser(
        "report-stage1-surface-baseline", help="aggregate repeated A/B HU+ baselines"
    )
    surface_report_parser.add_argument("manifest", type=Path)
    surface_report_parser.add_argument("--output", type=Path, required=True)

    generate_controls_parser = subparsers.add_parser(
        "generate-stage1-control-plans", help="execute frozen Stage 1D control-plan requests"
    )
    generate_controls_parser.add_argument("manifest", type=Path)
    generate_controls_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    control_selection = generate_controls_parser.add_mutually_exclusive_group(required=True)
    control_selection.add_argument("--job-id")
    control_selection.add_argument("--all", action="store_true")
    generate_controls_parser.add_argument(
        "--kind", choices=tuple(item.value for item in ControlPlanKind), required=True
    )
    generate_controls_parser.add_argument("--confirm-full-run")

    control_audit_parser = subparsers.add_parser(
        "prepare-stage1-control-audit",
        help="write the behavior-blinded Stage 1D control-plan audit",
    )
    control_audit_parser.add_argument("manifest", type=Path)
    control_audit_parser.add_argument(
        "--kind", choices=tuple(item.value for item in ControlPlanKind), required=True
    )
    control_audit_parser.add_argument("--tokenizer", type=Path, required=True)
    control_audit_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    control_audit_parser.add_argument("--output", type=Path, required=True)

    validate_control_audit_parser = subparsers.add_parser(
        "validate-stage1-control-audit", help="validate a completed Stage 1D control audit"
    )
    validate_control_audit_parser.add_argument("audit", type=Path)
    validate_control_audit_parser.add_argument("manifest", type=Path)

    render_control_parser = subparsers.add_parser(
        "prepare-stage1-render-control",
        help="freeze one 120-job stratified renderer substitution control",
    )
    render_control_parser.add_argument("plan_manifest", type=Path)
    render_control_parser.add_argument(
        "--kind", choices=tuple(item.value for item in RendererControlKind), required=True
    )
    render_control_parser.add_argument("--control-plan-manifest", type=Path)
    render_control_parser.add_argument("--control-plan-audit", type=Path)
    render_control_parser.add_argument("--run-id", required=True)
    render_control_parser.add_argument("--config", type=Path, default=Path("config/stage1.toml"))
    render_control_parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    render_control_parser.add_argument("--run-directory", type=Path, required=True)

    stage1_report_parser = subparsers.add_parser(
        "report-stage1", help="apply Stage 1E gates to natural and control outcomes"
    )
    stage1_report_parser.add_argument("--stage0-report", type=Path, required=True)
    stage1_report_parser.add_argument("--natural-behavior", type=Path, required=True)
    stage1_report_parser.add_argument("--opposite-behavior", type=Path, required=True)
    stage1_report_parser.add_argument("--shuffled-behavior", type=Path, required=True)
    stage1_report_parser.add_argument("--wrong-clause-behavior", type=Path, required=True)
    stage1_report_parser.add_argument("--length-report", type=Path, required=True)
    stage1_report_parser.add_argument("--plan-audit", type=Path, required=True)
    stage1_report_parser.add_argument("--wrong-clause-control-audit", type=Path, required=True)
    stage1_report_parser.add_argument("--clause-order-control-audit", type=Path, required=True)
    stage1_report_parser.add_argument("--control-plan-manifest", type=Path, required=True)
    stage1_report_parser.add_argument("--output", type=Path, required=True)
    stage1_report_parser.add_argument("--final-manual-review-passed", action="store_true")
    add_stage2_parsers(subparsers)
    add_stage3_parsers(subparsers)
    add_stage4_parsers(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stage2_exit = handle_stage2_command(args)
        if stage2_exit is not None:
            return stage2_exit
        stage3_exit = handle_stage3_command(args)
        if stage3_exit is not None:
            return stage3_exit
        stage4_exit = handle_stage4_command(args)
        if stage4_exit is not None:
            return stage4_exit
        if args.command == "validate-config":
            config = load_stage0_config(args.path)
            print(
                f"valid Stage 0 config: {len(config.task_paths)} tasks, "
                f"{len(config.conditions)} conditions, model {config.hosted_kimi.model}"
            )
        elif args.command == "validate-stage1-config":
            stage1_config = load_stage1_config(args.path)
            plans = (
                len(stage1_config.task_paths)
                * 2
                * len(stage1_config.formats)
                * len(stage1_config.concision_levels)
                * stage1_config.plans_per_cell
            )
            print(
                f"valid Stage 1A config: {len(stage1_config.task_paths)} tasks, "
                f"{plans} plans, {plans * stage1_config.renders_per_plan} renders, "
                f"model {stage1_config.hosted_kimi.model}"
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
        elif args.command == "stage1-kimi-preflight":
            stage1_config = load_stage1_config(args.config)
            preflight = provider_preflight(stage1_config.hosted_kimi)
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
                    "recovery requires both --recovery-from-manifest and --authorize-retry-job-id"
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
            print(f"prepared {len(manifest.jobs)} immutable requests at {run_directory.resolve()}")
        elif args.command == "generate-stage0":
            manifest = load_manifest(args.manifest)
            if args.dry_run:
                run_directory = args.manifest.resolve().parent
                completed = sum((run_directory / job.result_path).exists() for job in manifest.jobs)
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
                unambiguous_applicable_clauses=_audit_choice(args.applicable_clause_audit),
                distractors_genuinely_irrelevant=_audit_choice(args.distractor_audit),
                notes=args.dataset_audit_notes,
            )
            report = build_stage0_report(args.manifest, dataset_audit)
            if not report.complete and not args.allow_incomplete:
                raise ScoringError(
                    f"report is incomplete ({report.scored_jobs}/{report.expected_jobs}); "
                    "finish evaluation or pass --allow-incomplete"
                )
            output_directory = args.manifest.resolve().parent / "reports" / args.report_id
            write_stage0_report(report, output_directory)
            print(f"wrote Stage 0 report to {output_directory}: {report.recommendation.value}")
            if report.recommendation in {
                OverallRecommendation.INCOMPLETE,
                OverallRecommendation.INVALID_TASK_OR_TESTS,
                OverallRecommendation.STOP_OR_PIVOT,
            }:
                return 1
        elif args.command == "prepare-stage1-plans":
            stage1_config = load_stage1_config(args.config)
            stage1_run_directory = args.run_directory or (
                args.repository_root / stage1_config.artifacts_dir / "stage1" / args.run_id
            )
            plan_manifest = prepare_stage1_plans(
                stage1_config, args.repository_root, stage1_run_directory, args.run_id
            )
            print(
                f"prepared {len(plan_manifest.jobs)} immutable planner requests at "
                f"{stage1_run_directory.resolve()}"
            )
        elif args.command == "recover-stage1-plans":
            stage1_config = load_stage1_config(args.config)
            stage1_run_directory = args.run_directory or (
                args.repository_root / stage1_config.artifacts_dir / "stage1" / args.run_id
            )
            plan_manifest = prepare_stage1_plan_recovery(
                stage1_config,
                args.repository_root,
                args.source_manifest,
                stage1_run_directory,
                args.run_id,
                tuple(args.retry_job_id),
            )
            print(
                f"prepared Stage 1 planner recovery with "
                f"{len(plan_manifest.carried_forward_result_sha256s)} carried and "
                f"{len(plan_manifest.reparsed_source_result_sha256s)} reparsed results at "
                f"{stage1_run_directory.resolve()}"
            )
        elif args.command == "generate-stage1-plans":
            plan_manifest = load_plan_manifest(args.manifest)
            if args.dry_run:
                complete = sum(
                    (args.manifest.resolve().parent / job.result_path).is_file()
                    for job in plan_manifest.jobs
                )
                print(
                    f"dry run: {plan_manifest.run_id}, "
                    f"{len(plan_manifest.jobs)} total plans, "
                    f"{complete} complete; no API calls made"
                )
            else:
                _require_stage1_live_selection(
                    args.job_id, args.all, args.confirm_full_run, plan_manifest.run_id
                )
                if args.all:
                    require_plan_canary(args.manifest)
                stage1_client = stage1_client_from_environment(plan_manifest.provider)
                plan_summary = run_stage1_plans(args.manifest, stage1_client, job_id=args.job_id)
                print(plan_summary.model_dump_json(indent=2))
        elif args.command == "prepare-stage1-renders":
            stage1_config = load_stage1_config(args.config)
            stage1_run_directory = args.run_directory or (
                args.repository_root / stage1_config.artifacts_dir / "stage1" / args.run_id
            )
            render_manifest = prepare_stage1_renders(
                stage1_config,
                args.repository_root,
                args.plan_manifest,
                stage1_run_directory,
                args.run_id,
            )
            print(
                f"prepared {len(render_manifest.jobs)} immutable renderer requests at "
                f"{stage1_run_directory.resolve()}"
            )
        elif args.command == "generate-stage1-renders":
            render_manifest = load_render_manifest(args.manifest)
            if args.dry_run:
                complete = sum(
                    (args.manifest.resolve().parent / job.result_path).is_file()
                    for job in render_manifest.jobs
                )
                print(
                    f"dry run: {render_manifest.run_id}, "
                    f"{len(render_manifest.jobs)} total renders, "
                    f"{complete} complete; no API calls made"
                )
            else:
                _require_stage1_live_selection(
                    args.job_id, args.all, args.confirm_full_run, render_manifest.run_id
                )
                if args.all:
                    require_render_canary(args.manifest)
                stage1_client = stage1_client_from_environment(render_manifest.provider)
                render_summary = run_stage1_renders(
                    args.manifest, stage1_client, job_id=args.job_id
                )
                print(render_summary.model_dump_json(indent=2))
        elif args.command == "evaluate-stage1-renders":
            render_manifest = load_render_manifest(args.manifest)
            stage1_backend = (
                UnsafeLocalSandbox(render_manifest.sandbox)
                if args.unsafe_local
                else DockerSandbox(render_manifest.sandbox)
            )
            stage1_evaluation_summary = evaluate_stage1_renders(
                args.manifest,
                args.repository_root,
                stage1_backend,
                job_id=args.job_id,
            )
            print(stage1_evaluation_summary.model_dump_json(indent=2))
        elif args.command == "status-stage1a":
            status = build_stage1a_status(args.plan_manifest, args.render_manifest)
            serialized = status.model_dump_json(indent=2)
            if args.output is None:
                print(serialized)
            else:
                if args.output.exists():
                    raise Stage1Error(f"status output already exists: {args.output}")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(f"{serialized}\n", encoding="utf-8")
                print(f"wrote Stage 1A status: {args.output}")
        elif args.command == "fetch-stage1-tokenizer":
            digest = fetch_kimi_tokenizer(args.output)
            print(f"verified Kimi-K2.6 tokenizer: {digest}")
        elif args.command == "analyze-stage1-lengths":
            length_report = build_length_report(args.plan_manifest, args.tokenizer, args.output)
            print(
                f"wrote {len(length_report.rows)} exact plan lengths and "
                f"{len(length_report.nearest_length_matches)} within-task matches: "
                f"{args.output}"
            )
        elif args.command == "prepare-stage1-plan-audit":
            audit = prepare_plan_audit(args.plan_manifest, args.repository_root, args.output)
            print(f"wrote {len(audit.rows)} behavior-blinded plan-audit rows: {args.output}")
        elif args.command == "summarize-stage1-plan-audit":
            summary = summarize_plan_audit(args.audit, args.plan_manifest)
            print(summary.model_dump_json(indent=2))
        elif args.command == "report-stage1-behavior":
            metrics = build_behavioral_metrics(
                args.render_manifest,
                args.plan_manifest,
                args.plan_audit,
                args.surface_baseline,
                args.stage0_report,
                args.output,
            )
            print(
                f"wrote {metrics.evaluated_rows}/{metrics.expected_rows} Stage 1 outcomes: "
                f"{args.output}"
            )
        elif args.command == "prepare-stage1-control-plans":
            stage1_config = load_stage1_config(args.config)
            control_manifest = prepare_control_plans(
                stage1_config,
                args.repository_root,
                args.plan_manifest,
                args.run_directory,
                args.run_id,
                args.tokenizer,
            )
            print(f"prepared {len(control_manifest.jobs)} control plans: {args.run_directory}")
        elif args.command == "prepare-stage1-surface-baseline":
            stage1_config = load_stage1_config(args.config)
            baseline_manifest = prepare_surface_baseline(
                stage1_config, args.repository_root, args.run_directory, args.run_id
            )
            print(f"prepared {len(baseline_manifest.jobs)} surface baseline jobs")
        elif args.command == "generate-stage1-surface-baseline":
            baseline_run_id = args.manifest.resolve().parent.name
            if args.all and args.confirm_full_run != baseline_run_id:
                raise Stage1Error("--confirm-full-run must equal the baseline run directory name")
            if args.all:
                require_surface_baseline_canary(args.manifest)
            baseline_manifest = SurfaceBaselineManifest.model_validate_json(
                args.manifest.read_text(encoding="utf-8")
            )
            baseline_client = stage1_client_from_environment(baseline_manifest.provider)
            baseline_summary = run_surface_baseline(
                args.manifest,
                baseline_client,
                job_id=None if args.all else args.job_id,
            )
            print(json.dumps(baseline_summary, indent=2, sort_keys=True))
        elif args.command == "evaluate-stage1-surface-baseline":
            baseline_manifest = SurfaceBaselineManifest.model_validate_json(
                args.manifest.read_text(encoding="utf-8")
            )
            baseline_backend = (
                UnsafeLocalSandbox(baseline_manifest.sandbox)
                if args.unsafe_local
                else DockerSandbox(baseline_manifest.sandbox)
            )
            print(
                json.dumps(
                    evaluate_surface_baseline(
                        args.manifest,
                        args.repository_root,
                        baseline_backend,
                        job_id=args.job_id,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "report-stage1-surface-baseline":
            baseline_report = report_surface_baseline(args.manifest, args.output)
            print(
                f"wrote {baseline_report.evaluated}/{baseline_report.expected} surface outcomes: "
                f"{args.output}"
            )
        elif args.command == "generate-stage1-control-plans":
            if args.all and args.confirm_full_run != args.manifest.resolve().parent.name:
                raise Stage1Error("--confirm-full-run must equal the control run directory name")
            if args.all:
                require_control_plan_canary(args.manifest, ControlPlanKind(args.kind))
            stage1_config = load_stage1_config(args.config)
            control_client = stage1_client_from_environment(stage1_config.hosted_kimi)
            control_summary = run_control_plans(
                args.manifest,
                control_client,
                args.config,
                job_id=None if args.all else args.job_id,
                kind=ControlPlanKind(args.kind),
            )
            print(json.dumps(control_summary, indent=2, sort_keys=True))
        elif args.command == "prepare-stage1-control-audit":
            control_audit = prepare_control_plan_audit(
                args.manifest,
                args.repository_root,
                args.output,
                ControlPlanKind(args.kind),
                args.tokenizer,
            )
            print(f"wrote {len(control_audit.rows)} control audit rows: {args.output}")
        elif args.command == "validate-stage1-control-audit":
            print(
                json.dumps(
                    validate_control_plan_audit(args.audit, args.manifest),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "prepare-stage1-render-control":
            stage1_config = load_stage1_config(args.config)
            control_render_manifest = prepare_renderer_control(
                stage1_config,
                args.repository_root,
                args.plan_manifest,
                args.run_directory,
                args.run_id,
                RendererControlKind(args.kind),
                control_plan_manifest_path=args.control_plan_manifest,
                control_plan_audit_path=args.control_plan_audit,
            )
            print(
                f"prepared {len(control_render_manifest.jobs)} {args.kind} renders: "
                f"{args.run_directory}"
            )
        elif args.command == "report-stage1":
            stage1_report = build_stage1_report(
                args.stage0_report,
                args.natural_behavior,
                args.opposite_behavior,
                args.shuffled_behavior,
                args.wrong_clause_behavior,
                args.length_report,
                args.plan_audit,
                args.wrong_clause_control_audit,
                args.clause_order_control_audit,
                args.control_plan_manifest,
                args.output,
                final_manual_review_passed=args.final_manual_review_passed,
            )
            print(f"wrote Stage 1 report: {args.output} ({stage1_report.recommendation.value})")
            if stage1_report.recommendation is not Stage1Recommendation.CONTINUE_TO_STAGE2:
                return 1
    except (
        ConfigLoadError,
        GenerationError,
        HarnessError,
        ScoringError,
        Stage1Error,
        Stage2Error,
        Stage3Error,
        Stage4Error,
    ) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


def _require_stage1_live_selection(
    job_id: str | None, all_jobs: bool, confirmation: str | None, run_id: str
) -> None:
    if job_id is None and not all_jobs:
        raise Stage1Error(
            "live generation requires one explicit --job-id or --all with confirmation"
        )
    if all_jobs and confirmation != run_id:
        raise Stage1Error("--all requires --confirm-full-run with the exact manifest run ID")


def _audit_choice(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "passed"


def _require_canary_artifacts(manifest_path: Path, manifest: GenerationManifest) -> None:
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
            if job.task_id == first_task_id and job.condition is condition and job.sample_index == 0
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
            generation.thinking_requested != "enabled" or not generation.reasoning_content_present
        ):
            raise GenerationError(
                f"full generation is locked: thinking evidence is missing for {job.job_id}"
            )

        candidate_path = _checked_canary_path(run_directory, generation.candidate_path, "candidate")
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
