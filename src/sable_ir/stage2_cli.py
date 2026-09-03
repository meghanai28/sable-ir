"""Stage 2 subcommands, kept apart from `cli.py` so the Stage 1 track can evolve independently."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from sable_ir.harness import DockerSandbox, SandboxBackend, UnsafeLocalSandbox
from sable_ir.schema import SandboxConfig
from sable_ir.stage2 import (
    Stage2Error,
    audit_stage2_preflight,
    build_stage2_reference_corpus,
    complete_stage2_reference_audit,
    freeze_stage2_dataset,
    freeze_stage2_split,
    load_stage2_config,
    prepare_stage2_reference_audit,
    prepare_stage2_training_manifest,
    validate_stage2_reference_audit,
)
from sable_ir.stage2_local import (
    EvalKind,
    LocalGeneration,
    LocalGenerator,
    Role,
    TransformersLocalGenerator,
    build_run_summary,
    build_stage2_eval_report,
    evaluate_stage2_eval,
    load_eval_manifest,
    prepare_stage2_eval,
    prepare_stage2_plan_audit,
    run_stage2_eval,
    run_stage2_sandbox_smoke,
    select_stage2_checkpoint,
)
from sable_ir.stage2_train import run_stage2_model_canary, run_stage2_training

STAGE2_COMMANDS = frozenset(
    {
        "validate-stage2-config",
        "freeze-stage2-split",
        "build-stage2-reference-corpus",
        "prepare-stage2-reference-audit",
        "validate-stage2-reference-audit",
        "complete-stage2-reference-audit",
        "stage2-preflight",
        "stage2-sandbox-smoke",
        "stage2-model-canary",
        "freeze-stage2-dataset",
        "prepare-stage2-training",
        "train-stage2",
        "prepare-stage2-eval",
        "run-stage2-eval",
        "status-stage2-eval",
        "evaluate-stage2-eval",
        "prepare-stage2-plan-audit",
        "report-stage2-eval",
        "select-stage2-checkpoint",
    }
)


def add_stage2_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    def common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", type=Path, default=Path("config/stage2.toml"))
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        return parser

    subparsers.add_parser("validate-stage2-config", help="validate Stage 2 TOML").add_argument(
        "path", type=Path
    )
    common(subparsers.add_parser("freeze-stage2-split", help="freeze the base-task split"))
    common(
        subparsers.add_parser(
            "build-stage2-reference-corpus",
            help="expand authored reference plans across paraphrase axes",
        )
    )
    common(
        subparsers.add_parser(
            "prepare-stage2-reference-audit", help="write the behavior-blinded audit template"
        )
    )
    common(
        subparsers.add_parser(
            "validate-stage2-reference-audit", help="check the completed reference audit"
        )
    )
    common(
        subparsers.add_parser(
            "complete-stage2-reference-audit",
            help="expand the reviewer's per-plan decisions file into the row-level audit",
        )
    )
    preflight = common(
        subparsers.add_parser("stage2-preflight", help="record PC/data readiness checks")
    )
    preflight.add_argument("--output", type=Path, required=True)
    preflight.add_argument("--stage1-gate-override", help="recorded reason for bypassing the gate")
    preflight.add_argument("--skip-sandbox-check", action="store_true")
    smoke = common(
        subparsers.add_parser(
            "stage2-sandbox-smoke", help="run the A/B references through the amd64 sandbox"
        )
    )
    smoke.add_argument("--output", type=Path, required=True)
    smoke.add_argument("--unsafe-local", action="store_true")
    common(
        subparsers.add_parser(
            "stage2-model-canary",
            help="NF4 load + one full-length training step + generation for the active model (GPU)",
        )
    )
    freeze = common(
        subparsers.add_parser("freeze-stage2-dataset", help="freeze audited JSONL by split")
    )
    freeze.add_argument("--destination", type=Path, required=True)
    training = common(
        subparsers.add_parser("prepare-stage2-training", help="authorize one training run")
    )
    training.add_argument("--dataset-manifest", type=Path, required=True)
    training.add_argument("--run-id", required=True)
    training.add_argument("--run-directory", type=Path)
    training.add_argument("--stage1-gate-override")
    train = subparsers.add_parser("train-stage2", help="train the planner adapter (GPU)")
    train.add_argument("manifest", type=Path)
    train.add_argument("--confirm", required=True, help="must equal the frozen run ID")
    train.add_argument("--repository-root", type=Path, default=Path.cwd())
    prepare_eval = common(
        subparsers.add_parser("prepare-stage2-eval", help="freeze a local planner/renderer run")
    )
    prepare_eval.add_argument("--run-id", required=True)
    prepare_eval.add_argument("--kind", choices=tuple(k.value for k in EvalKind), required=True)
    prepare_eval.add_argument("--run-directory", type=Path)
    prepare_eval.add_argument("--adapter", type=Path, help="checkpoint directory (omit = base)")
    prepare_eval.add_argument("--training-result", type=Path)
    prepare_eval.add_argument("--checkpoint-selection", type=Path)
    prepare_eval.add_argument("--no-direct", action="store_true")
    run_eval = subparsers.add_parser("run-stage2-eval", help="generate plans/renders/direct (GPU)")
    run_eval.add_argument("manifest", type=Path)
    run_eval.add_argument("--repository-root", type=Path, default=Path.cwd())
    run_eval.add_argument(
        "--phase", choices=("plans", "renders", "direct"), action="append", dest="phases"
    )
    run_eval.add_argument("--limit", type=int)
    run_eval.add_argument(
        "--dry-run",
        action="store_true",
        help="deterministic offline stand-in generator for wiring checks; never for results",
    )
    status = subparsers.add_parser("status-stage2-eval", help="show generation progress")
    status.add_argument("manifest", type=Path)
    evaluate = subparsers.add_parser(
        "evaluate-stage2-eval", help="run sandbox suites on generated candidates"
    )
    evaluate.add_argument("manifest", type=Path)
    evaluate.add_argument("--repository-root", type=Path, default=Path.cwd())
    evaluate.add_argument("--job-id")
    evaluate.add_argument("--limit", type=int)
    evaluate.add_argument("--unsafe-local", action="store_true")
    plan_audit = subparsers.add_parser(
        "prepare-stage2-plan-audit", help="write the behavior-blinded plan audit packet"
    )
    plan_audit.add_argument("manifest", type=Path)
    plan_audit.add_argument("--repository-root", type=Path, default=Path.cwd())
    plan_audit.add_argument("--output", type=Path, required=True)
    report = subparsers.add_parser("report-stage2-eval", help="aggregate one local eval run")
    report.add_argument("manifest", type=Path)
    report.add_argument("--repository-root", type=Path, default=Path.cwd())
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--plan-audit", type=Path)
    select = subparsers.add_parser(
        "select-stage2-checkpoint", help="choose the adapter from dev reports only"
    )
    select.add_argument("--report", type=Path, action="append", required=True, dest="reports")
    select.add_argument("--training-result", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)


def handle_stage2_command(args: argparse.Namespace) -> int | None:
    """Return an exit code for Stage 2 commands, or None when the command belongs elsewhere."""
    if args.command not in STAGE2_COMMANDS:
        return None
    if args.command == "validate-stage2-config":
        config = load_stage2_config(args.path)
        print(
            json.dumps(
                {
                    "design_mode": config.design_mode.value,
                    "tasks": len(config.task_paths),
                    "model": config.model.active_model_id,
                    "revision": config.model.active_revision,
                    "sandbox_platform": config.sandbox.platform,
                }
            )
        )
        return 0
    if args.command == "freeze-stage2-split":
        split = freeze_stage2_split(args.config, args.repository_root)
        print(json.dumps({name.value: count for name, count in split.counts.items()}))
        return 0
    if args.command == "build-stage2-reference-corpus":
        corpus = build_stage2_reference_corpus(args.config, args.repository_root)
        print(json.dumps({"rows": len(corpus.rows), "author": corpus.author}))
        return 0
    if args.command == "prepare-stage2-reference-audit":
        audit = prepare_stage2_reference_audit(args.config, args.repository_root)
        print(json.dumps({"rows": len(audit.rows), "corpus_sha256": audit.corpus_sha256}))
        return 0
    if args.command == "validate-stage2-reference-audit":
        summary = validate_stage2_reference_audit(args.config, args.repository_root)
        print(summary.model_dump_json())
        return 0 if summary.ready_for_freeze else 1
    if args.command == "complete-stage2-reference-audit":
        completed = complete_stage2_reference_audit(args.config, args.repository_root)
        print(completed.model_dump_json())
        return 0 if completed.ready_for_freeze else 1
    if args.command == "stage2-preflight":
        report = audit_stage2_preflight(
            args.config,
            args.repository_root,
            args.output,
            stage1_gate_override=args.stage1_gate_override,
            check_sandbox=not args.skip_sandbox_check,
        )
        for check in report.checks:
            print(f"[{'ok' if check.passed else 'FAIL'}] {check.check}: {check.detail}")
        print(
            json.dumps(
                {
                    "ready_for_dataset_freeze": report.ready_for_dataset_freeze,
                    "ready_for_training": report.ready_for_training,
                }
            )
        )
        return 0 if report.ready_for_training else 1
    if args.command == "stage2-sandbox-smoke":
        config = load_stage2_config(args.config)
        backend = _backend(config.sandbox, args.unsafe_local)
        smoke = run_stage2_sandbox_smoke(args.config, args.repository_root, backend, args.output)
        for row in smoke.rows:
            marker = "ok" if row.expected_pattern_holds else "FAIL"
            print(f"[{marker}] {row.task_id}/{row.policy.value}")
        return 0 if smoke.passed else 1
    if args.command == "stage2-model-canary":
        canary = run_stage2_model_canary(args.config, args.repository_root)
        print(
            json.dumps(
                {
                    "model": canary.model_id,
                    "passed": canary.passed,
                    "peak_gpu_memory_gib": canary.peak_gpu_memory_gib,
                    "training_step_loss": canary.training_step_loss,
                    "error": canary.error,
                }
            )
        )
        return 0 if canary.passed else 1
    if args.command == "freeze-stage2-dataset":
        dataset = freeze_stage2_dataset(args.config, args.repository_root, args.destination)
        print(
            json.dumps(
                {name.value: item.rows for name, item in dataset.files.items()}
                | {"design_mode": dataset.design_mode.value}
            )
        )
        return 0
    if args.command == "prepare-stage2-training":
        config = load_stage2_config(args.config)
        run_directory = args.run_directory or (
            args.repository_root / config.artifacts_dir / "training" / args.run_id
        )
        training_manifest = prepare_stage2_training_manifest(
            args.config,
            args.repository_root,
            args.dataset_manifest,
            run_directory,
            args.run_id,
            stage1_gate_override=args.stage1_gate_override,
        )
        print(
            json.dumps(
                {
                    "run_id": training_manifest.run_id,
                    "model": training_manifest.model.active_model_id,
                    "gpu": training_manifest.gpu_name,
                    "manifest": str(run_directory / "manifest.json"),
                    "stage1_gate_override": training_manifest.stage1_gate_override,
                }
            )
        )
        return 0
    if args.command == "train-stage2":
        result = run_stage2_training(args.manifest, args.repository_root, args.confirm)
        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "checkpoints": [c.directory for c in result.checkpoints],
                    "trainable_fraction": result.trainable_fraction,
                    "peak_gpu_memory_gib": result.peak_gpu_memory_gib,
                }
            )
        )
        return 0
    if args.command == "prepare-stage2-eval":
        config = load_stage2_config(args.config)
        run_directory = args.run_directory or (
            args.repository_root / config.artifacts_dir / "eval" / args.run_id
        )
        eval_manifest = prepare_stage2_eval(
            args.config,
            args.repository_root,
            run_directory,
            args.run_id,
            EvalKind(args.kind),
            adapter_directory=args.adapter,
            training_result_path=args.training_result,
            checkpoint_selection_path=args.checkpoint_selection,
            include_direct=not args.no_direct,
        )
        print(
            json.dumps(
                {
                    "run_id": eval_manifest.run_id,
                    "kind": eval_manifest.kind.value,
                    "tasks": [t.task_id for t in eval_manifest.tasks],
                    "plan_jobs": len(eval_manifest.plan_jobs),
                    "render_jobs": len(eval_manifest.render_jobs),
                    "direct_jobs": len(eval_manifest.direct_jobs),
                    "manifest": str(run_directory / "manifest.json"),
                }
            )
        )
        return 0
    if args.command == "run-stage2-eval":
        run_manifest = load_eval_manifest(args.manifest)
        root = args.repository_root.resolve()
        config_path = root / run_manifest.config_path
        if hashlib.sha256(config_path.read_bytes()).hexdigest() != run_manifest.config_sha256:
            raise Stage2Error("Stage 2 config changed after the eval run was frozen")
        config = load_stage2_config(config_path)
        generator: LocalGenerator
        if args.dry_run:
            generator = DryRunGenerator()
        else:
            adapter = run_manifest.planner_adapter
            generator = TransformersLocalGenerator(
                config,
                root / adapter.directory if adapter is not None else None,
                expected_adapter_hashes=adapter.adapter_file_sha256s if adapter else None,
            )
        run_summary = run_stage2_eval(
            args.manifest,
            generator,
            phases=tuple(args.phases) if args.phases else ("plans", "renders", "direct"),
            limit=args.limit,
        )
        print(run_summary.model_dump_json())
        return 0
    if args.command == "status-stage2-eval":
        print(build_run_summary(args.manifest, {}).model_dump_json())
        return 0
    if args.command == "evaluate-stage2-eval":
        evaluated_manifest = load_eval_manifest(args.manifest)
        backend = _backend(evaluated_manifest.sandbox, args.unsafe_local)
        summary_eval = evaluate_stage2_eval(
            args.manifest, args.repository_root, backend, job_id=args.job_id, limit=args.limit
        )
        print(summary_eval.model_dump_json())
        return 0
    if args.command == "prepare-stage2-plan-audit":
        packet = prepare_stage2_plan_audit(args.manifest, args.repository_root, args.output)
        print(json.dumps({"rows": len(packet.rows), "output": str(args.output)}))
        return 0
    if args.command == "report-stage2-eval":
        eval_report = build_stage2_eval_report(
            args.manifest, args.repository_root, args.output, plan_audit_path=args.plan_audit
        )
        print(
            json.dumps(
                {
                    "run_id": eval_report.run_id,
                    "kind": eval_report.kind.value,
                    "pilot": eval_report.pilot,
                    "complete": eval_report.complete,
                    "selection_metric_value": eval_report.selection_metric_value,
                    "model_floor": eval_report.model_floor.recommendation,
                    "stage1_gate": eval_report.stage1_gate.value,
                    "stage2_status": eval_report.stage2_status,
                    "bottleneck_limits_capability": (
                        eval_report.bottleneck_sanity.bottleneck_limits_capability
                    ),
                    "invalid_task_or_tests": eval_report.invalid_task_or_tests,
                }
            )
        )
        return 0
    if args.command == "select-stage2-checkpoint":
        selection = select_stage2_checkpoint(args.reports, args.training_result, args.output)
        print(
            json.dumps(
                {
                    "selected_adapter": selection.selected_adapter.directory,
                    "metric": selection.selected_metric_value,
                    "candidates": selection.candidates,
                }
            )
        )
        return 0
    raise AssertionError(f"unhandled Stage 2 command {args.command}")


class DryRunGenerator:
    """Offline stand-in that emits well-formed but content-free output for wiring checks."""

    def generate(
        self, prompt: str, *, role: Role, max_new_tokens: int, seed: int
    ) -> LocalGeneration:
        if role is Role.PLANNER:
            if "FORMAT: STRUCTURED" in prompt:
                text = (
                    "SOURCE: dry run\nTRUST: dry run\nSINK: dry run\nGUARD: dry run\n"
                    "ORDER: dry run\nEFFECT: dry run\nEND_PLAN"
                )
            else:
                text = "Dry-run freeform plan.\nEND_PLAN"
        else:
            text = "```python\nraise NotImplementedError('dry run')\n```"
        return LocalGeneration(
            text=text,
            prompt_tokens=len(prompt.split()),
            output_tokens=len(text.split()),
            finish_reason="stop",
            latency_seconds=0.0,
            seed=seed,
        )

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def describe(self) -> dict[str, str]:
        return {"backend": "dry-run", "warning": "not a model; results are meaningless"}


def _backend(config: SandboxConfig, unsafe_local: bool) -> SandboxBackend:
    if unsafe_local:
        return UnsafeLocalSandbox(config)
    return DockerSandbox(config)
