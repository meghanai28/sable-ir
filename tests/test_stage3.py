"""Stage 3 track tests: paraphrase split, activation dataset, probes, and the report (no GPU)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sable_ir.harness import EvaluationResult, ExecutionResult, RunStatus
from sable_ir.schema import PolicyValue
from sable_ir.stage1_analysis import AuditConfidence, ClauseSelection, PolicyVisibility
from sable_ir.stage2 import (
    DesignMode,
    SplitName,
    Stage1GateStatus,
    freeze_stage2_split,
    load_stage2_config,
)
from sable_ir.stage2_local import (
    AdapterRef,
    BottleneckSanity,
    EvalKind,
    LocalGeneration,
    ModelFloorVerdict,
    Stage2CheckpointSelection,
    Stage2EvalReport,
)
from sable_ir.stage2_train import hash_tree
from sable_ir.stage3 import (
    BoundaryState,
    CapturedState,
    ParaphraseSet,
    PlanCapture,
    Stage3Error,
    Stage3ParaphraseAudit,
    Stage3PlanAudit,
    assemble_stage3_dataset,
    load_activation_manifest,
    load_stage3_config,
    prepare_stage3_activations,
    prepare_stage3_paraphrase_audit,
    prepare_stage3_plan_audit,
    run_stage3_activations,
    validate_policy_paraphrases,
    validate_stage3_config,
    validate_stage3_paraphrase_audit,
)
from sable_ir.stage3_cli import DryRunCapturer

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")

SOURCE_ROOT = Path(__file__).resolve().parents[1]
DIGEST = "a" * 64


def _copy_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    shutil.copytree(SOURCE_ROOT / "tasks", root / "tasks")
    shutil.copytree(SOURCE_ROOT / "data" / "stage2", root / "data" / "stage2")
    shutil.copytree(SOURCE_ROOT / "data" / "stage3", root / "data" / "stage3")
    # Tests start from an unreviewed packet so prepare/complete can be exercised.
    (root / "data" / "stage3" / "paraphrase-audit.json").unlink(missing_ok=True)
    (root / "config").mkdir()
    shutil.copy(SOURCE_ROOT / "config" / "stage2.toml", root / "config" / "stage2.toml")
    stage3_text = (SOURCE_ROOT / "config" / "stage3.toml").read_text(encoding="utf-8")
    stage3_text = stage3_text.replace("expected_num_layers = 32", "expected_num_layers = 4")
    stage3_text = stage3_text.replace("hidden_size = 2560", "hidden_size = 16")
    stage3_text = stage3_text.replace("evenly_spaced_every = 4", "evenly_spaced_every = 2")
    stage3_text = stage3_text.replace("candidate_region_start = 14", "candidate_region_start = 1")
    stage3_text = stage3_text.replace("candidate_region_end = 24", "candidate_region_end = 2")
    stage3_text = stage3_text.replace(
        'formats = ["structured", "freeform"]', 'formats = ["structured"]'
    )
    stage3_text = stage3_text.replace(
        'concision_levels = ["full", "concise", "minimal"]', 'concision_levels = ["full"]'
    )
    stage3_text = stage3_text.replace("renders_per_plan = 3", "renders_per_plan = 1")
    (root / "config" / "stage3.toml").write_text(stage3_text, encoding="utf-8")
    # Split hashes bind the copied task bytes.
    (root / "data" / "stage2" / "split.json").unlink()
    freeze_stage2_split(root / "config" / "stage2.toml", root)
    return root, root / "config" / "stage2.toml", root / "config" / "stage3.toml"


def _complete_paraphrase_audit(root: Path, config_path: Path) -> None:
    if not (root / load_stage3_config(config_path).paraphrase_audit_path).exists():
        prepare_stage3_paraphrase_audit(config_path, root)
    path = root / load_stage3_config(config_path).paraphrase_audit_path
    audit = Stage3ParaphraseAudit.model_validate_json(path.read_text(encoding="utf-8"))
    filled = audit.model_copy(
        update={
            "reviewer": "test-reviewer",
            "completed_at": datetime.now(UTC).isoformat(),
            "rows": tuple(
                row.model_copy(
                    update={"preserves_assigned_policy": True, "framing_label_correct": True}
                )
                for row in audit.rows
            ),
        }
    )
    path.write_text(filled.model_dump_json(indent=2) + "\n", encoding="utf-8")
    assert validate_stage3_paraphrase_audit(config_path, root).ready_for_activations


def _write_stage2_handoff(
    root: Path, *, recommendation: str = "continue_with_primary_model"
) -> None:
    adapter_dir = (
        root / "artifacts" / "stage2" / "training" / "sft-01" / "checkpoints" / "checkpoint-54"
    )
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "adapter_model.safetensors").write_bytes(b"fake-adapter")
    hashes = hash_tree(adapter_dir, adapter_only=True)
    adapter = AdapterRef(
        directory=adapter_dir.relative_to(root).as_posix(),
        adapter_file_sha256s=hashes,
        training_run_id="sft-01",
        global_step=54,
        training_stage1_gate_override="pilot started before Stage 1 finished",
    )
    selection = Stage2CheckpointSelection(
        created_at="2026-09-04T00:00:00+00:00",
        training_run_id="sft-01",
        training_result_sha256=DIGEST,
        candidates={adapter.directory: 0.5},
        report_sha256s={"artifacts/stage2/eval/dev-54/report.json": DIGEST},
        selected_adapter=adapter,
        selected_metric_value=0.5,
    )
    selection_path = root / "artifacts" / "stage2" / "selection.json"
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    selection_path.write_text(selection.model_dump_json(indent=2) + "\n", encoding="utf-8")
    stage2 = load_stage2_config(root / "config" / "stage2.toml")
    passed = recommendation == "continue_with_primary_model"
    floor = Stage2EvalReport(
        created_at="2026-09-04T00:00:00+00:00",
        run_id="floor-01",
        kind=EvalKind.MODEL_FLOOR,
        design_mode=DesignMode.PILOT,
        pilot=True,
        splits_used=(SplitName.TRAIN, SplitName.DEV, SplitName.TEST),
        eval_manifest_sha256=DIGEST,
        plan_audit_sha256=None,
        planner_adapter=adapter,
        model=stage2.model,
        stage1_gate=Stage1GateStatus.PENDING,
        stage1_report_sha256=None,
        stage2_status="provisional_pending_stage1",
        training_stage1_gate_override="pilot started before Stage 1 finished",
        complete=True,
        expected_render_rows=1,
        evaluated_render_rows=1,
        expected_direct_rows=1,
        evaluated_direct_rows=1,
        invalid_task_or_tests=False,
        rows=(),
        direct_rows=(),
        by_format_and_concision={},
        by_format_and_length_bin={},
        by_task={},
        direct_by_condition={},
        surface_only_assigned_baseline_by_policy={PolicyValue.A: 0.1, PolicyValue.B: 0.1},
        excess_hidden_use_by_policy={PolicyValue.A: 0.0, PolicyValue.B: 0.0},
        selection_metric_value=0.5,
        model_floor=ModelFloorVerdict(
            threshold=0.3,
            full_document_direct_assigned_and_functional=0.5,
            full_structured_plan_assigned_and_functional=0.4,
            full_freeform_plan_assigned_and_functional=0.4,
            tasks_covered=5,
            passed=passed,
            recommendation=recommendation,  # type: ignore[arg-type]
            rationale="test fixture",
        ),
        bottleneck_sanity=BottleneckSanity(
            functional_max_drop=0.05,
            assigned_policy_max_drop=0.10,
            full_document_direct_functional=0.8,
            full_structured_plan_functional=0.8,
            full_document_direct_assigned_and_functional=0.5,
            full_structured_plan_assigned_and_functional=0.4,
            functional_within_tolerance=True,
            assigned_policy_within_tolerance=True,
            bottleneck_limits_capability=False,
        ),
        planner_output_tokens=1,
        renderer_output_tokens=1,
        planner_latency_seconds=0.1,
        renderer_latency_seconds=0.1,
    )
    floor_path = root / "artifacts" / "stage2" / "eval" / "floor-01" / "report.json"
    floor_path.parent.mkdir(parents=True)
    floor_path.write_text(floor.model_dump_json(indent=2) + "\n", encoding="utf-8")


class SignalCapturer:
    """Offline capturer: well-formed plans, G encoded in activations from the document phrasing."""

    def __init__(self, layers: tuple[int, ...], hidden: int, paraphrases: Any) -> None:
        self._layers = layers
        self._hidden = hidden
        self._phrases: list[tuple[str, float]] = []
        for per_policy in paraphrases.tasks.values():
            for policy, item in per_policy.items():
                signal = 1.0 if policy is PolicyValue.B else -1.0
                for which in ParaphraseSet:
                    for phrasing in item.phrasings(which):
                        self._phrases.append((phrasing.text, signal))
        self._pending = 0.0

    @property
    def layers(self) -> tuple[int, ...]:
        return self._layers

    def _signal(self, prompt: str) -> float:
        for text, signal in self._phrases:
            if text in prompt:
                return signal
        return 0.0

    def _state(self, state: BoundaryState, signal: float) -> CapturedState:
        values = np.zeros((len(self._layers), self._hidden), dtype=np.float32)
        values[:, 0] = signal
        return CapturedState(
            state=state,
            token_index=0,
            token_text="END_PLAN" if state is not BoundaryState.PLANNER_INPUT else "<tok>",
            layers=self._layers,
            values=values,
        )

    def generate_plan(self, prompt: str, *, max_new_tokens: int, seed: int) -> PlanCapture:
        del max_new_tokens
        signal = self._signal(prompt)
        if "Safety policy document" in prompt and signal == 0.0:
            raise AssertionError("fixture capturer did not recover G from the planner prompt")
        self._pending = signal
        text = (
            "SOURCE: input\nTRUST: untrusted\nSINK: operation\nGUARD: validate before the sink\n"
            "ORDER: guard then sink\nEFFECT: return the result\nEND_PLAN"
        )
        return PlanCapture(
            generation=_generation(text, prompt, seed),
            states=(
                self._state(BoundaryState.PLANNER_INPUT, signal),
                self._state(BoundaryState.PLANNER_OUTPUT, signal),
            ),
        )

    def capture_renderer_ingestion(self, prompt: str) -> CapturedState | None:
        if "END_PLAN" not in prompt:
            return None
        return self._state(BoundaryState.RENDERER_INGESTION, self._pending)

    def capture_last_token(self, prompt: str) -> CapturedState:
        return self._state(BoundaryState.RENDERER_INGESTION, 0.0)

    def generate_code(self, prompt: str, *, max_new_tokens: int, seed: int) -> LocalGeneration:
        del max_new_tokens
        return _generation("```python\nraise NotImplementedError('fixture')\n```", prompt, seed)

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def describe(self) -> dict[str, str]:
        return {"backend": "test-signal"}


def _generation(text: str, prompt: str, seed: int) -> LocalGeneration:
    return LocalGeneration(
        text=text,
        prompt_tokens=len(prompt.split()),
        output_tokens=len(text.split()),
        finish_reason="stop",
        latency_seconds=0.0,
        seed=seed,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_fake_evaluations(root: Path, manifest_path: Path) -> None:
    manifest = load_activation_manifest(manifest_path)
    run_directory = manifest_path.parent
    manifest_sha = _sha(manifest_path.read_bytes())
    passed = ExecutionResult(status=RunStatus.PASSED, exit_code=0, duration_seconds=0.01)
    failed = ExecutionResult(status=RunStatus.FAILED, exit_code=1, duration_seconds=0.01)
    plan_by_id = {job.job_id: job for job in manifest.plan_jobs}
    from sable_ir.schema import TestSuiteKind
    from sable_ir.stage2_local import CandidateResult
    from sable_ir.stage3 import Stage3EvaluationArtifact

    for render in manifest.render_jobs:
        result = CandidateResult.model_validate_json(
            (run_directory / render.result_path).read_text(encoding="utf-8")
        )
        if result.candidate_sha256 is None:
            continue
        plan = plan_by_id[render.plan_job_id]
        evaluation = EvaluationResult(
            task_id=plan.task_id,
            candidate_sha256=result.candidate_sha256,
            backend="test",
            compile=passed,
            suites={
                TestSuiteKind.FUNCTIONALITY: passed,
                TestSuiteKind.POLICY_A: passed if plan.assigned_policy is PolicyValue.A else failed,
                TestSuiteKind.POLICY_B: passed if plan.assigned_policy is PolicyValue.B else failed,
                TestSuiteKind.ORIGINAL_SECURITY: passed,
            },
        )
        artifact = Stage3EvaluationArtifact(
            job_id=render.job_id,
            manifest_sha256=manifest_sha,
            candidate_sha256=result.candidate_sha256,
            evaluation=evaluation,
        )
        path = run_directory / f"jobs/{render.job_id}/evaluation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _complete_plan_audit(path: Path) -> None:
    audit = Stage3PlanAudit.model_validate_json(path.read_text(encoding="utf-8"))
    rows = []
    for row in audit.rows:
        set_name = ParaphraseSet.SET1 if "__set1__" in row.job_id else ParaphraseSet.SET2
        preserved = set_name is ParaphraseSet.SET1
        applicable = row.applicable_clause_ids
        rows.append(
            row.model_copy(
                update={
                    "audited_without_generated_code": True,
                    "clause_selection": ClauseSelection.CORRECT,
                    "policy_visibility": (
                        PolicyVisibility.PRESERVED if preserved else PolicyVisibility.OMITTED
                    ),
                    "selected_clause_ids": applicable,
                    "irrelevant_clause_ids_included": (),
                    "confidence": AuditConfidence.CONFIDENT,
                }
            )
        )
    filled = audit.model_copy(
        update={
            "rows": tuple(rows),
            "reviewer": "test-reviewer",
            "completed_at": datetime.now(UTC).isoformat(),
        }
    )
    path.write_text(filled.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _run_capture(root: Path, stage3_path: Path) -> Path:
    _complete_paraphrase_audit(root, stage3_path)
    _write_stage2_handoff(root)
    run_dir = root / "artifacts" / "stage3" / "activations" / "act-01"
    manifest = prepare_stage3_activations(stage3_path, root, run_dir, "act-01")
    from sable_ir.stage3 import Stage3PolicyParaphrases

    paraphrases = Stage3PolicyParaphrases.model_validate_json(
        (root / load_stage3_config(stage3_path).policy_paraphrases_path).read_text(encoding="utf-8")
    )
    capturer = SignalCapturer(manifest.layers, manifest.hidden_size, paraphrases)
    run_stage3_activations(run_dir / "manifest.json", capturer)
    _write_fake_evaluations(root, run_dir / "manifest.json")
    return run_dir


class TestParaphrases:
    def test_checked_in_paraphrases_pass_and_cover_both_framings(self) -> None:
        from sable_ir.config import load_task
        from sable_ir.stage2 import Stage2ReferencePlans, load_stage2_config
        from sable_ir.stage3 import Stage3PolicyParaphrases

        stage2 = load_stage2_config(SOURCE_ROOT / "config" / "stage2.toml")
        tasks = {spec.id: spec for spec in (load_task(SOURCE_ROOT / p) for p in stage2.task_paths)}
        paraphrases = Stage3PolicyParaphrases.model_validate_json(
            (SOURCE_ROOT / "data" / "stage3" / "policy-paraphrases.json").read_text(
                encoding="utf-8"
            )
        )
        plans = Stage2ReferencePlans.model_validate_json(
            (SOURCE_ROOT / stage2.reference_plans_path).read_text(encoding="utf-8")
        )
        validation = validate_policy_paraphrases(paraphrases, tasks, plans)
        assert validation.passed
        assert all(check.passed for check in validation.checks)

    def test_set2_sharing_a_six_gram_with_set1_fails(self) -> None:
        from sable_ir.config import load_task
        from sable_ir.stage2 import load_stage2_config
        from sable_ir.stage3 import Stage3PolicyParaphrases

        stage2 = load_stage2_config(SOURCE_ROOT / "config" / "stage2.toml")
        tasks = {spec.id: spec for spec in (load_task(SOURCE_ROOT / p) for p in stage2.task_paths)}
        paraphrases = Stage3PolicyParaphrases.model_validate_json(
            (SOURCE_ROOT / "data" / "stage3" / "policy-paraphrases.json").read_text(
                encoding="utf-8"
            )
        )
        task_id = next(iter(paraphrases.tasks))
        item = paraphrases.tasks[task_id][PolicyValue.A]
        stolen = item.set1[0].text
        broken = item.model_copy(
            update={"set2": (item.set2[0].model_copy(update={"text": stolen}), item.set2[1])}
        )
        tasks_map = dict(paraphrases.tasks)
        per_policy = dict(tasks_map[task_id])
        per_policy[PolicyValue.A] = broken
        tasks_map[task_id] = per_policy
        mutated = paraphrases.model_copy(update={"tasks": tasks_map})
        validation = validate_policy_paraphrases(mutated, tasks, None)
        assert not validation.passed


class TestActivationTrack:
    def test_probe_weights_use_all_rows_but_equalize_base_tasks(self) -> None:
        from sable_ir.stage3_analysis import task_balanced_weights

        tasks = np.array(["large"] * 8 + ["small"] * 4)
        labels = np.array([0] * 4 + [1] * 4 + [0] * 2 + [1] * 2, dtype=np.int64)
        weights = task_balanced_weights(tasks, labels)
        assert len(weights) == len(labels)
        assert weights[tasks == "large"].sum() == pytest.approx(weights[tasks == "small"].sum())

    def test_config_summary_and_paraphrase_audit(self, tmp_path: Path) -> None:
        root, _stage2, stage3 = _copy_repo(tmp_path)
        summary = validate_stage3_config(stage3, root)
        assert summary.plan_jobs == 40  # 5 tasks x 2 policies x 2 sets x 2 phrasings x 1x1
        assert summary.render_jobs == 40
        assert summary.surface_only_jobs == 10
        assert summary.paraphrases.passed
        assert not summary.paraphrase_audit_ready
        prepare_stage3_paraphrase_audit(stage3, root)
        assert not validate_stage3_paraphrase_audit(stage3, root).ready_for_activations
        _complete_paraphrase_audit(root, stage3)
        assert validate_stage3_config(stage3, root).paraphrase_audit_ready

    def test_model_floor_gate_blocks_prepare(self, tmp_path: Path) -> None:
        root, _stage2, stage3 = _copy_repo(tmp_path)
        _complete_paraphrase_audit(root, stage3)
        _write_stage2_handoff(root, recommendation="stop_or_pivot")
        with pytest.raises(Stage3Error, match="model floor"):
            prepare_stage3_activations(
                stage3, root, root / "artifacts" / "stage3" / "activations" / "blocked", "blocked"
            )

    def test_capture_labels_probes_and_report(self, tmp_path: Path) -> None:
        from sable_ir.stage3_analysis import (
            Stage3Report,
            build_stage3_report,
            evaluate_stage3_heldout,
            fit_stage3_probes,
        )

        root, _stage2, stage3 = _copy_repo(tmp_path)
        run_dir = _run_capture(root, stage3)
        manifest = load_activation_manifest(run_dir / "manifest.json")
        assert len(manifest.plan_jobs) == 40
        assert manifest.renderer_adapter_enabled is False
        assert manifest.pilot is True

        primary_path = run_dir / "plan-audit.json"
        double_path = run_dir / "plan-audit.double.json"
        prepare_stage3_plan_audit(run_dir / "manifest.json", root, primary_path, kind="primary")
        prepare_stage3_plan_audit(run_dir / "manifest.json", root, double_path, kind="double")
        _complete_plan_audit(primary_path)
        _complete_plan_audit(double_path)
        dataset_path = run_dir / "dataset.json"
        dataset = assemble_stage3_dataset(
            run_dir / "manifest.json", root, primary_path, double_path, dataset_path
        )
        assert dataset.complete
        assert dataset.agreement.reliable
        assert dataset.quadrant_counts.get("faithful_success", 0) > 0
        assert dataset.quadrant_counts.get("hidden_use", 0) > 0
        # Double audit covers every held-out plan.
        double = json.loads(double_path.read_text(encoding="utf-8"))
        test_jobs = {job.job_id for job in manifest.plan_jobs if job.split is SplitName.TEST}
        assert test_jobs <= {row["job_id"] for row in double["rows"]}

        analysis_dir = root / "artifacts" / "stage3" / "analysis" / "fit-01"
        selection = fit_stage3_probes(dataset_path, root, analysis_dir)
        assert selection.probe_layer[BoundaryState.PLANNER_INPUT] in manifest.layers
        renderer_layer = selection.direction_layer[BoundaryState.RENDERER_INGESTION]
        assert renderer_layer is not None
        assert (
            f"renderer_ingestion:L{renderer_layer}:from_prohibition_to_permission"
            in selection.control_directions
        )
        probe_fit = json.loads((analysis_dir / "probes-dev.json").read_text(encoding="utf-8"))
        assert probe_fit["probe_training_unit"] == "activation_row"
        assert (
            probe_fit["probe_task_weighting"]
            == "equal_total_weight_per_base_task_policy"
        )
        assert probe_fit["direction_estimation_unit"] == "task_level_ab_difference_only"
        assert probe_fit["uncertainty_unit"] == "base_task_cluster"
        heldout_path = analysis_dir / "heldout.json"
        heldout = evaluate_stage3_heldout(analysis_dir / "selection.json", root, heldout_path)
        by_state = {state.state: state for state in heldout.states}
        planner = by_state[BoundaryState.PLANNER_INPUT]
        assert planner.decodable, planner.test
        assert planner.test_set2.auroc is not None, planner.test_set2
        assert planner.test_set2.auroc >= 0.75, planner.test_set2
        assert planner.transfers_to_set2
        # Surface-only renderer states carry no G signal, so the probe should not decode them.
        surface = by_state[BoundaryState.RENDERER_INGESTION].surface_only_control
        assert surface is not None
        assert surface.auroc is None or surface.auroc < 0.75

        report = build_stage3_report(
            analysis_dir / "selection.json",
            heldout_path,
            root,
            analysis_dir / "report.json",
        )
        assert report.pilot is True
        assert report.status.stage3_status == "provisional_pending_stage1"
        assert report.probe_generalizes
        requirements = report.stage4_authorization_requirements
        omitted = report.primary_renderer_ingestion_analysis.omitted_or_blurred
        assert requirements["renderer_ingestion_decodable"] == (
            omitted.support_status == "supported"
            and omitted.renderer_ingestion is not None
            and omitted.renderer_ingestion.auroc is not None
            and omitted.renderer_ingestion.auroc >= 0.75
        )
        assert requirements["renderer_ingestion_transfers_to_paraphrase_set2"]
        assert report.causal_evaluation_authorized == all(requirements.values())
        assert (
            report.renderer_ingestion_decodability_scope
            == "heldout_supported_omitted_or_blurred_plans"
        )
        assert (
            report.primary_renderer_ingestion_analysis.surface_only_control_role
            == "negative_control_balanced_counterfactual_labels_without_policy_input"
        )
        assert not report.primary_renderer_ingestion_analysis.pooled_probe_accuracy_is_headline
        assert (
            report.primary_renderer_ingestion_analysis.headline
            == "renderer_ingestion_on_omitted_or_blurred_plans"
        )
        assert "policy-orientation" in report.policy_orientation_scope
        assert "path_symlink_report" in report.fact_specific_transfer_scope
        assert "none: mechanistic case study" in report.generalization_claim

        unsupported = omitted.model_copy(
            update={
                "support_status": "insufficient_quadrant_support",
                "renderer_ingestion": None,
                "best_text_baseline": None,
                "best_text": None,
                "activation_minus_text_auroc": None,
            }
        )
        unsupported_primary = report.primary_renderer_ingestion_analysis.model_copy(
            update={"omitted_or_blurred": unsupported}
        )
        with pytest.raises(
            ValidationError,
            match="renderer_ingestion_decodable must describe the supported held-out",
        ):
            Stage3Report.model_validate(
                {
                    **report.model_dump(),
                    "primary_renderer_ingestion_analysis": unsupported_primary.model_dump(),
                    "stage4_authorization_requirements": {
                        **report.stage4_authorization_requirements,
                        "renderer_ingestion_decodable": True,
                    },
                    "causal_evaluation_authorized": True,
                }
            )

    def test_dry_run_capturer_is_well_formed(self) -> None:
        capturer = DryRunCapturer((1, 2), 8)
        capture = capturer.generate_plan(
            "FORMAT: STRUCTURED\nDETAIL: FULL\nplease plan", max_new_tokens=16, seed=1
        )
        assert capture.generation.text.endswith("END_PLAN")
        assert {s.state for s in capture.states} == {
            BoundaryState.PLANNER_INPUT,
            BoundaryState.PLANNER_OUTPUT,
        }
