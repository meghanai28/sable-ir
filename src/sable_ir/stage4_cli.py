"""Stage 4 command-line surface; GPU imports remain lazy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sable_ir.harness import DockerSandbox, UnsafeLocalSandbox
from sable_ir.stage4 import (
    Stage4Error,
    build_stage4_report,
    evaluate_stage4_full_run,
    load_stage4_config,
    prepare_recipient_audit,
    prepare_stage4_experiment,
    prepare_stage4_full_run,
    select_stage4_sanity,
    validate_stage4_config,
)

STAGE4_COMMANDS = frozenset(
    {
        "validate-stage4-config",
        "prepare-stage4-recipient-audit",
        "prepare-stage4-experiment",
        "materialize-stage4-directions",
        "run-stage4-sanity",
        "select-stage4-sanity",
        "prepare-stage4-full-run",
        "run-stage4-full",
        "evaluate-stage4-full",
        "report-stage4",
    }
)


def add_stage4_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    def common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", type=Path, default=Path("config/stage4.toml"))
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        return parser

    common(
        subparsers.add_parser(
            "validate-stage4-config", help="validate frozen Stage 4 paths and thresholds"
        )
    )
    audit = common(
        subparsers.add_parser(
            "prepare-stage4-recipient-audit",
            help="write the behavior-blinded source/recipient selection packet",
        )
    )
    audit.add_argument("--output", type=Path)
    experiment = common(
        subparsers.add_parser(
            "prepare-stage4-experiment",
            help="freeze authorized Stage 3 handoff, recipients, controls, and strengths",
        )
    )
    experiment.add_argument("--run-id", required=True)
    experiment.add_argument("--run-directory", type=Path)
    materialize = common(
        subparsers.add_parser(
            "materialize-stage4-directions",
            help="capture/derive all Stage 4 controls with the adapter-disabled renderer (GPU)",
        )
    )
    materialize.add_argument("experiment_manifest", type=Path)
    materialize.add_argument("--output", type=Path, required=True)
    sanity = common(
        subparsers.add_parser(
            "run-stage4-sanity",
            help="run development-only KL/logit/teacher-forced checks (GPU)",
        )
    )
    sanity.add_argument("experiment_manifest", type=Path)
    sanity.add_argument("direction_set", type=Path)
    sanity.add_argument("--output-directory", type=Path, required=True)
    select = common(
        subparsers.add_parser(
            "select-stage4-sanity",
            help="select a development strength or stop before full code generation",
        )
    )
    select.add_argument("experiment_manifest", type=Path)
    select.add_argument("--result", type=Path, action="append", required=True, dest="results")
    select.add_argument("--output", type=Path, required=True)
    full = common(
        subparsers.add_parser(
            "prepare-stage4-full-run", help="freeze the held-out single-position job matrix"
        )
    )
    full.add_argument("experiment_manifest", type=Path)
    full.add_argument("sanity_selection", type=Path)
    full.add_argument("direction_set", type=Path)
    full.add_argument("--run-id", required=True)
    full.add_argument("--run-directory", type=Path, required=True)
    run = common(
        subparsers.add_parser(
            "run-stage4-full", help="generate held-out code with single END_PLAN edits (GPU)"
        )
    )
    run.add_argument("manifest", type=Path)
    run.add_argument("--limit", type=int)
    evaluate = common(
        subparsers.add_parser(
            "evaluate-stage4-full", help="sandbox Stage 4 candidate implementations"
        )
    )
    evaluate.add_argument("manifest", type=Path)
    evaluate.add_argument("--unsafe-local", action="store_true")
    report = common(
        subparsers.add_parser(
            "report-stage4", help="apply bidirectionality/control/functionality success rules"
        )
    )
    report.add_argument("manifest", type=Path)
    report.add_argument("--output", type=Path, required=True)


def handle_stage4_command(args: argparse.Namespace) -> int | None:
    if args.command not in STAGE4_COMMANDS:
        return None
    if args.command == "validate-stage4-config":
        summary = validate_stage4_config(args.config, args.repository_root)
        print(summary.model_dump_json(indent=2))
        return 0
    if args.command == "prepare-stage4-recipient-audit":
        config = load_stage4_config(args.config)
        output = args.output or args.repository_root / config.recipient_audit_path
        audit = prepare_recipient_audit(args.config, args.repository_root, output)
        print(json.dumps({"candidates": len(audit.candidates), "output": str(output)}))
        return 0
    if args.command == "prepare-stage4-experiment":
        config = load_stage4_config(args.config)
        directory = args.run_directory or (
            args.repository_root / config.artifacts_dir / "experiments" / args.run_id
        )
        experiment_manifest = prepare_stage4_experiment(
            args.config, args.repository_root, directory, args.run_id
        )
        print(
            json.dumps(
                {
                    "run_id": experiment_manifest.run_id,
                    "selected_layer": experiment_manifest.selected_layer,
                    "recipients": len(experiment_manifest.recipients),
                    "manifest": str(directory / "manifest.json"),
                }
            )
        )
        return 0
    if args.command == "materialize-stage4-directions":
        from sable_ir.stage4_runtime import materialize_stage4_directions

        result = materialize_stage4_directions(
            args.experiment_manifest, args.repository_root, args.output
        )
        print(json.dumps({"directions": len(result.artifacts), "output": str(args.output)}))
        return 0
    if args.command == "run-stage4-sanity":
        from sable_ir.stage4_runtime import run_stage4_sanity

        rows = run_stage4_sanity(
            args.experiment_manifest,
            args.direction_set,
            args.repository_root,
            args.output_directory,
        )
        print(json.dumps({"sanity_pairs": len(rows), "output": str(args.output_directory)}))
        return 0
    if args.command == "select-stage4-sanity":
        selection = select_stage4_sanity(
            args.experiment_manifest,
            tuple(args.results),
            args.repository_root,
            args.output,
        )
        print(selection.model_dump_json(indent=2))
        return 0 if selection.passed else 1
    if args.command == "prepare-stage4-full-run":
        full_manifest = prepare_stage4_full_run(
            args.experiment_manifest,
            args.sanity_selection,
            args.direction_set,
            args.repository_root,
            args.run_directory,
            args.run_id,
        )
        print(json.dumps({"jobs": len(full_manifest.jobs), "manifest": str(args.run_directory)}))
        return 0
    if args.command == "run-stage4-full":
        from sable_ir.stage4_runtime import run_stage4_full

        completed = run_stage4_full(args.manifest, args.repository_root, limit=args.limit)
        print(json.dumps({"newly_completed": completed}))
        return 0
    if args.command == "evaluate-stage4-full":
        from sable_ir.stage4 import Stage4FullRunManifest, _load

        evaluation_manifest = _load(Stage4FullRunManifest, args.manifest)
        backend = (
            UnsafeLocalSandbox(evaluation_manifest.sandbox)
            if args.unsafe_local
            else DockerSandbox(evaluation_manifest.sandbox)
        )
        evaluated = evaluate_stage4_full_run(args.manifest, args.repository_root, backend)
        print(json.dumps({"newly_evaluated": evaluated}))
        return 0
    if args.command == "report-stage4":
        report = build_stage4_report(args.manifest, args.repository_root, args.output)
        print(report.model_dump_json(indent=2))
        return 0 if report.complete and report.status == "complete" else 1
    raise Stage4Error(f"unhandled Stage 4 command: {args.command}")
