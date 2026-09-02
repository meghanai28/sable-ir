"""Small validation CLI; experiment commands are added at later checkpoints."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from sable_ir.config import ConfigLoadError, load_stage0_config, load_task
from sable_ir.schema import Stage0Config, TaskSpec, json_schema_for


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sable-ir")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("validate-config", help="validate Stage 0 TOML")
    config_parser.add_argument("path", type=Path)

    task_parser = subparsers.add_parser("validate-task", help="validate task JSON")
    task_parser.add_argument("paths", type=Path, nargs="+")

    schema_parser = subparsers.add_parser("print-schema", help="print a JSON Schema")
    schema_parser.add_argument("kind", choices=("stage0-config", "task"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            config = load_stage0_config(args.path)
            print(
                f"valid Stage 0 config: {len(config.task_paths)} tasks, "
                f"{len(config.conditions)} conditions"
            )
        elif args.command == "validate-task":
            for path in args.paths:
                task = load_task(path)
                print(f"valid task: {task.id}")
        elif args.command == "print-schema":
            model = Stage0Config if args.kind == "stage0-config" else TaskSpec
            print(json.dumps(json_schema_for(model), indent=2, sort_keys=True))
    except ConfigLoadError as error:
        print(error)
        return 2
    return 0

