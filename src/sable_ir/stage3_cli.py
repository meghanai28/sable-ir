"""Stage 3 subcommands, kept apart from `cli.py` like the Stage 2 set.

The numpy/scikit-learn analysis module is imported inside the handlers so the `sable-ir` entry
point keeps working in environments without the `stage3` extra.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from sable_ir.harness import DockerSandbox, SandboxBackend, UnsafeLocalSandbox
from sable_ir.schema import SandboxConfig
from sable_ir.stage2 import load_stage2_config
from sable_ir.stage2_local import LocalGeneration
from sable_ir.stage3 import (
    ActivationCapturer,
    AuditKind,
    BoundaryState,
    CapturedState,
    PlanCapture,
    Stage3Error,
    assemble_stage3_dataset,
    build_stage3_run_summary,
    evaluate_stage3_activations,
    load_activation_manifest,
    load_stage3_config,
    prepare_stage3_activations,
    prepare_stage3_paraphrase_audit,
    prepare_stage3_plan_audit,
    run_stage3_activations,
    validate_stage3_config,
    validate_stage3_paraphrase_audit,
)

STAGE3_COMMANDS = frozenset(
    {
        "validate-stage3-config",
        "prepare-stage3-paraphrase-audit",
        "validate-stage3-paraphrase-audit",
        "prepare-stage3-activations",
        "run-stage3-activations",
        "status-stage3-activations",
        "evaluate-stage3-activations",
        "prepare-stage3-plan-audit",
        "prepare-stage3-double-audit",
        "assemble-stage3-dataset",
        "fit-stage3-probes",
        "evaluate-stage3-heldout",
        "report-stage3",
    }
)


def add_stage3_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    def common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", type=Path, default=Path("config/stage3.toml"))
        parser.add_argument("--repository-root", type=Path, default=Path.cwd())
        return parser

    common(
        subparsers.add_parser(
            "validate-stage3-config",
            help="validate Stage 3 TOML, paraphrase sets, rubric; print layers and job counts",
        )
    )
    common(
        subparsers.add_parser(
            "prepare-stage3-paraphrase-audit",
            help="write the meaning-review packet for every authored policy phrasing",
        )
    )
    common(
        subparsers.add_parser(
            "validate-stage3-paraphrase-audit",
            help="check that every policy phrasing passed meaning review",
        )
    )
    prepare = common(
        subparsers.add_parser(
            "prepare-stage3-activations",
            help="freeze the activation-dataset job matrix (requires Stage 2 selection + floor)",
        )
    )
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--run-directory", type=Path)
    run = common(
        subparsers.add_parser(
            "run-stage3-activations", help="generate plans/code and capture boundary states (GPU)"
        )
    )
    run.add_argument("manifest", type=Path)
    run.add_argument(
        "--phase", dest="phases", action="append", choices=["plans", "renders", "controls"]
    )
    run.add_argument("--limit", type=int)
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="offline stand-in capturer with random states; wiring checks only",
    )
    subparsers.add_parser("status-stage3-activations", help="show capture progress").add_argument(
        "manifest", type=Path
    )
    evaluate = common(
        subparsers.add_parser(
            "evaluate-stage3-activations", help="run rendered candidates through the sandbox"
        )
    )
    evaluate.add_argument("manifest", type=Path)
    evaluate.add_argument("--limit", type=int)
    evaluate.add_argument("--unsafe-local", action="store_true")
    for name, help_text in (
        ("prepare-stage3-plan-audit", "write the blinded primary label packet (every plan)"),
        (
            "prepare-stage3-double-audit",
            "write the blinded second-reviewer packet (all held-out plans + seeded sample)",
        ),
    ):
        packet = common(subparsers.add_parser(name, help=help_text))
        packet.add_argument("manifest", type=Path)
        packet.add_argument("--output", type=Path, required=True)
    assemble = common(
        subparsers.add_parser(
            "assemble-stage3-dataset",
            help="join captures, sandbox outcomes, and both audits into the frozen dataset",
        )
    )
    assemble.add_argument("manifest", type=Path)
    assemble.add_argument("--plan-audit", type=Path, required=True)
    assemble.add_argument("--double-audit", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    fit = common(
        subparsers.add_parser(
            "fit-stage3-probes",
            help="dev phase: fit probes, estimate directions, freeze selection.json",
        )
    )
    fit.add_argument("--dataset", type=Path, required=True)
    fit.add_argument("--output-dir", type=Path, required=True)
    heldout = common(
        subparsers.add_parser(
            "evaluate-stage3-heldout",
            help="score held-out tasks and paraphrase set 2 with the frozen selection",
        )
    )
    heldout.add_argument("--selection", type=Path, required=True)
    heldout.add_argument("--output", type=Path, required=True)
    report = common(subparsers.add_parser("report-stage3", help="write the Stage 3 report"))
    report.add_argument("--selection", type=Path, required=True)
    report.add_argument("--heldout", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)


def handle_stage3_command(args: argparse.Namespace) -> int | None:
    if args.command not in STAGE3_COMMANDS:
        return None
    if args.command == "validate-stage3-config":
        summary = validate_stage3_config(args.config, args.repository_root)
        print(summary.model_dump_json(indent=2))
        return 0 if summary.paraphrases.passed and summary.families_covered_by_rubric else 1
    if args.command == "prepare-stage3-paraphrase-audit":
        audit = prepare_stage3_paraphrase_audit(args.config, args.repository_root)
        print(json.dumps({"rows": len(audit.rows)}))
        return 0
    if args.command == "validate-stage3-paraphrase-audit":
        paraphrase_summary = validate_stage3_paraphrase_audit(args.config, args.repository_root)
        print(paraphrase_summary.model_dump_json())
        return 0 if paraphrase_summary.ready_for_activations else 1
    if args.command == "prepare-stage3-activations":
        config = load_stage3_config(args.config)
        run_directory = args.run_directory or (
            args.repository_root / config.artifacts_dir / "activations" / args.run_id
        )
        manifest = prepare_stage3_activations(
            args.config, args.repository_root, run_directory, args.run_id
        )
        print(
            json.dumps(
                {
                    "run_id": manifest.run_id,
                    "layers": list(manifest.layers),
                    "plan_jobs": len(manifest.plan_jobs),
                    "render_jobs": len(manifest.render_jobs),
                    "surface_only_jobs": len(manifest.surface_only_jobs),
                    "planner_adapter": manifest.planner_adapter.directory,
                    "stage2_status_at_preparation": manifest.stage2_status_at_preparation,
                    "manifest": str(run_directory / "manifest.json"),
                }
            )
        )
        return 0
    if args.command == "run-stage3-activations":
        manifest = load_activation_manifest(args.manifest)
        root = args.repository_root.resolve()
        config_path = root / manifest.config_path
        if hashlib.sha256(config_path.read_bytes()).hexdigest() != manifest.config_sha256:
            raise Stage3Error("Stage 3 config changed after the run was frozen")
        capturer: ActivationCapturer
        if args.dry_run:
            capturer = DryRunCapturer(manifest.layers, manifest.hidden_size)
        else:
            from sable_ir.stage3 import TransformersActivationCapturer

            stage2_path = root / manifest.stage2_config_path
            if (
                hashlib.sha256(stage2_path.read_bytes()).hexdigest()
                != manifest.stage2_config_sha256
            ):
                raise Stage3Error("Stage 2 config changed after the run was frozen")
            capturer = TransformersActivationCapturer(
                load_stage2_config(stage2_path),
                root / manifest.planner_adapter.directory,
                expected_adapter_hashes=manifest.planner_adapter.adapter_file_sha256s,
                layers=manifest.layers,
                expected_num_layers=manifest.expected_num_layers,
                hidden_size=manifest.hidden_size,
            )
        run_summary = run_stage3_activations(
            args.manifest,
            capturer,
            phases=tuple(args.phases) if args.phases else ("plans", "renders", "controls"),
            limit=args.limit,
        )
        print(run_summary.model_dump_json())
        return 0
    if args.command == "status-stage3-activations":
        print(build_stage3_run_summary(args.manifest, {}).model_dump_json())
        return 0
    if args.command == "evaluate-stage3-activations":
        manifest = load_activation_manifest(args.manifest)
        backend = _backend(manifest.sandbox, args.unsafe_local)
        evaluation = evaluate_stage3_activations(
            args.manifest, args.repository_root, backend, limit=args.limit
        )
        print(evaluation.model_dump_json())
        return 0
    if args.command in ("prepare-stage3-plan-audit", "prepare-stage3-double-audit"):
        kind: AuditKind = "double" if args.command.endswith("double-audit") else "primary"
        packet = prepare_stage3_plan_audit(
            args.manifest, args.repository_root, args.output, kind=kind
        )
        print(json.dumps({"kind": kind, "rows": len(packet.rows), "output": str(args.output)}))
        return 0
    if args.command == "assemble-stage3-dataset":
        dataset = assemble_stage3_dataset(
            args.manifest, args.repository_root, args.plan_audit, args.double_audit, args.output
        )
        print(
            json.dumps(
                {
                    "rows": len(dataset.rows),
                    "complete": dataset.complete,
                    "quadrants": dataset.quadrant_counts,
                    "agreement_reliable": dataset.agreement.reliable,
                    "malformed_plans": dataset.malformed_plans,
                    "output": str(args.output),
                }
            )
        )
        return 0
    if args.command == "fit-stage3-probes":
        from sable_ir.stage3_analysis import fit_stage3_probes

        selection = fit_stage3_probes(args.dataset, args.repository_root, args.output_dir)
        print(
            json.dumps(
                {
                    "probe_layer": {k.value: v for k, v in selection.probe_layer.items()},
                    "direction_layer": {k.value: v for k, v in selection.direction_layer.items()},
                    "selection": str(args.output_dir / "selection.json"),
                }
            )
        )
        return 0
    if args.command == "evaluate-stage3-heldout":
        from sable_ir.stage3_analysis import evaluate_stage3_heldout

        heldout = evaluate_stage3_heldout(args.selection, args.repository_root, args.output)
        print(
            json.dumps(
                {
                    state.state.value: {
                        "test_auroc": state.test.auroc,
                        "set2_auroc": state.test_set2.auroc,
                        "decodable": state.decodable,
                        "beats_text": state.activations_beat_text,
                    }
                    for state in heldout.states
                }
            )
        )
        return 0
    if args.command == "report-stage3":
        from sable_ir.stage3_analysis import build_stage3_report

        report = build_stage3_report(
            args.selection, args.heldout, args.repository_root, args.output
        )
        print(
            json.dumps(
                {
                    "pilot": report.pilot,
                    "stage3_status": report.status.stage3_status,
                    "decodable": {k.value: v for k, v in report.decodable_by_state.items()},
                    "probe_generalizes": report.probe_generalizes,
                    "causal_evaluation_authorized": report.causal_evaluation_authorized,
                    "stop_or_pivot": report.stop_or_pivot,
                }
            )
        )
        return 0
    raise AssertionError(f"unhandled Stage 3 command {args.command}")


class DryRunCapturer:
    """Offline stand-in: well-formed plans, placeholder code, seeded random states.

    Its activations carry no information; outputs exist only to exercise file wiring.
    """

    def __init__(self, layers: tuple[int, ...], hidden_size: int) -> None:
        self._layers = layers
        self._hidden = hidden_size

    @property
    def layers(self) -> tuple[int, ...]:
        return self._layers

    def _state(self, state: BoundaryState, seed: int) -> CapturedState:
        import numpy as np

        values = np.random.default_rng(seed).standard_normal(
            (len(self._layers), self._hidden), dtype=np.float32
        )
        return CapturedState(
            state=state, token_index=0, token_text="<dry>", layers=self._layers, values=values
        )

    def generate_plan(self, prompt: str, *, max_new_tokens: int, seed: int) -> PlanCapture:
        text = (
            "SOURCE: dry run\nTRUST: dry run\nSINK: dry run\nGUARD: dry run\n"
            "ORDER: dry run\nEFFECT: dry run\nEND_PLAN"
            if "FORMAT: STRUCTURED" in prompt
            else "Dry-run freeform plan.\nEND_PLAN"
        )
        return PlanCapture(
            generation=_generation(text, prompt, seed),
            states=(
                self._state(BoundaryState.PLANNER_INPUT, seed),
                self._state(BoundaryState.PLANNER_OUTPUT, seed + 1),
            ),
        )

    def capture_renderer_ingestion(self, prompt: str) -> CapturedState | None:
        if "END_PLAN" not in prompt:
            return None
        return self._state(BoundaryState.RENDERER_INGESTION, len(prompt))

    def capture_last_token(self, prompt: str) -> CapturedState:
        return self._state(BoundaryState.RENDERER_INGESTION, len(prompt) + 7)

    def generate_code(self, prompt: str, *, max_new_tokens: int, seed: int) -> LocalGeneration:
        return _generation("```python\nraise NotImplementedError('dry run')\n```", prompt, seed)

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def describe(self) -> dict[str, str]:
        return {"backend": "dry-run", "warning": "not a model; states are random noise"}


def _generation(text: str, prompt: str, seed: int) -> LocalGeneration:
    return LocalGeneration(
        text=text,
        prompt_tokens=len(prompt.split()),
        output_tokens=len(text.split()),
        finish_reason="stop",
        latency_seconds=0.0,
        seed=seed,
    )


def _backend(config: SandboxConfig, unsafe_local: bool) -> SandboxBackend:
    if unsafe_local:
        return UnsafeLocalSandbox(config)
    return DockerSandbox(config)
