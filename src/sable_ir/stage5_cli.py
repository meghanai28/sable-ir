"""Command-line surface for post-experiment metrics and collision analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sable_ir.stage5 import (
    Stage5Error,
    assemble_stage5_observations,
    load_stage5_config,
    prepare_stage5_inputs,
    validate_stage5_config,
)
from sable_ir.stage5_analysis import (
    build_collision_index,
    build_stage5_final_report,
    build_stage5_metrics,
    export_stage5_tables,
    freeze_collision_taxonomy,
    prepare_development_collision_audit,
    prepare_heldout_collision_audit,
    report_collision_vocabulary,
)

STAGE5_COMMANDS = frozenset(
    {
        "validate-stage5-config",
        "prepare-stage5-inputs",
        "assemble-stage5-observations",
        "report-stage5-metrics",
        "index-stage5-collisions",
        "prepare-stage5-development-collision-audit",
        "freeze-stage5-collision-taxonomy",
        "prepare-stage5-heldout-collision-audit",
        "report-stage5-collision-vocabulary",
        "report-stage5-final",
        "export-stage5-tables",
    }
)


def add_stage5_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    def common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", type=Path, default=Path("config/stage5.toml"))
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        return parser

    common(subparsers.add_parser("validate-stage5-config", help="validate analysis-only setup"))
    prepare = common(
        subparsers.add_parser(
            "prepare-stage5-inputs", help="hash-freeze complete Stage 1-4 artifacts"
        )
    )
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    assemble = common(
        subparsers.add_parser(
            "assemble-stage5-observations", help="normalize immutable cross-stage outcomes"
        )
    )
    assemble.add_argument("manifest", type=Path)
    assemble.add_argument("--output", type=Path, required=True)
    metrics = common(
        subparsers.add_parser(
            "report-stage5-metrics", help="compute task-clustered monitorability and A/B metrics"
        )
    )
    metrics.add_argument("observations", type=Path)
    metrics.add_argument("--output", type=Path, required=True)
    collisions = common(
        subparsers.add_parser(
            "index-stage5-collisions", help="locate natural exact-plan A/B collisions"
        )
    )
    collisions.add_argument("observations", type=Path)
    collisions.add_argument("--output", type=Path, required=True)
    development = common(
        subparsers.add_parser(
            "prepare-stage5-development-collision-audit",
            help="expose train/dev collision diffs while withholding test collisions",
        )
    )
    development.add_argument("collision_index", type=Path)
    development.add_argument("--output", type=Path, required=True)
    development.add_argument("--diff-directory", type=Path, required=True)
    freeze = common(
        subparsers.add_parser(
            "freeze-stage5-collision-taxonomy", help="freeze completed development categories"
        )
    )
    freeze.add_argument("development_audit", type=Path)
    freeze.add_argument("--output", type=Path, required=True)
    heldout = common(
        subparsers.add_parser(
            "prepare-stage5-heldout-collision-audit",
            help="expose held-out collisions only after taxonomy freeze",
        )
    )
    heldout.add_argument("collision_index", type=Path)
    heldout.add_argument("taxonomy", type=Path)
    heldout.add_argument("--output", type=Path, required=True)
    heldout.add_argument("--diff-directory", type=Path, required=True)
    vocabulary = common(
        subparsers.add_parser(
            "report-stage5-collision-vocabulary",
            help="compute frozen-taxonomy coverage, novelty, accumulation, and recurrence",
        )
    )
    vocabulary.add_argument("collision_index", type=Path)
    vocabulary.add_argument("development_audit", type=Path)
    vocabulary.add_argument("taxonomy", type=Path)
    vocabulary.add_argument("heldout_audit", type=Path)
    vocabulary.add_argument("--output", type=Path, required=True)
    final = common(
        subparsers.add_parser(
            "report-stage5-final", help="bind proposal success-criterion results into one report"
        )
    )
    final.add_argument("metric_report", type=Path)
    final.add_argument("collision_report", type=Path)
    final.add_argument("--output", type=Path, required=True)
    export = common(
        subparsers.add_parser(
            "export-stage5-tables", help="export immutable plot-ready CSV metric tables"
        )
    )
    export.add_argument("metric_report", type=Path)
    export.add_argument("collision_report", type=Path)
    export.add_argument("final_report", type=Path)
    export.add_argument("--output-directory", type=Path, required=True)


def handle_stage5_command(args: argparse.Namespace) -> int | None:
    if args.command not in STAGE5_COMMANDS:
        return None
    config = load_stage5_config(args.config)
    root = args.repository_root.resolve()
    paths = config.inputs
    if args.command == "validate-stage5-config":
        print(validate_stage5_config(args.config, root).model_dump_json(indent=2))
        return 0
    if args.command == "prepare-stage5-inputs":
        prepared = prepare_stage5_inputs(args.config, root, args.output, args.run_id)
        print(prepared.model_dump_json(indent=2))
        return 0
    if args.command == "assemble-stage5-observations":
        observations = assemble_stage5_observations(args.manifest, root, args.output)
        print(json.dumps({"plans": len(observations.rows), "output": str(args.output)}))
        return 0
    if args.command == "report-stage5-metrics":
        metric_report = build_stage5_metrics(
            args.observations,
            config.analysis,
            root / paths.stage3_report_path,
            root / paths.stage4_report_path,
            args.output,
        )
        print(metric_report.model_dump_json(indent=2))
        return 0 if metric_report.status.value == "complete" else 1
    if args.command == "index-stage5-collisions":
        collision_index = build_collision_index(args.observations, args.output)
        print(json.dumps({"collisions": len(collision_index.records), "output": str(args.output)}))
        return 0 if collision_index.invalid_both_policy_outputs == 0 else 1
    if args.command == "prepare-stage5-development-collision-audit":
        development_audit = prepare_development_collision_audit(
            args.collision_index,
            root / config.collision_rubric_path,
            root,
            args.output,
            args.diff_directory,
        )
        print(json.dumps({"rows": len(development_audit.rows), "output": str(args.output)}))
        return 0
    if args.command == "freeze-stage5-collision-taxonomy":
        taxonomy = freeze_collision_taxonomy(
            args.development_audit, root / config.collision_rubric_path, args.output
        )
        print(json.dumps({"categories": len(taxonomy.categories), "output": str(args.output)}))
        return 0
    if args.command == "prepare-stage5-heldout-collision-audit":
        heldout_audit = prepare_heldout_collision_audit(
            args.collision_index,
            args.taxonomy,
            root,
            args.output,
            args.diff_directory,
        )
        print(json.dumps({"rows": len(heldout_audit.rows), "output": str(args.output)}))
        return 0
    if args.command == "report-stage5-collision-vocabulary":
        vocabulary_report = report_collision_vocabulary(
            args.collision_index,
            args.development_audit,
            args.taxonomy,
            args.heldout_audit,
            config.analysis.top_k,
            args.output,
        )
        print(vocabulary_report.model_dump_json(indent=2))
        return 0
    if args.command == "report-stage5-final":
        final_report = build_stage5_final_report(
            args.metric_report,
            args.collision_report,
            root / paths.stage1_report_path,
            root / paths.stage2_test_report_path,
            root / paths.stage3_report_path,
            root / paths.stage4_report_path,
            args.output,
        )
        print(final_report.model_dump_json(indent=2))
        return 0 if final_report.status == "complete" else 1
    if args.command == "export-stage5-tables":
        outputs = export_stage5_tables(
            args.metric_report,
            args.collision_report,
            args.final_report,
            args.output_directory,
        )
        print(json.dumps({"tables": [str(path) for path in outputs]}))
        return 0
    raise Stage5Error(f"unhandled Stage 5 command: {args.command}")
