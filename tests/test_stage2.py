"""Stage 2 track tests: data freeze, masking, LoRA guards, and the local eval loop (no GPU)."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sable_ir.harness import UnsafeLocalSandbox
from sable_ir.schema import PolicyValue, Stage0Condition, Stage1PlanFormat
from sable_ir.stage1_analysis import AuditConfidence, ClauseSelection, PolicyVisibility
from sable_ir.stage2 import (
    ReferencePlanDecisions,
    SplitName,
    Stage1GateStatus,
    Stage2Config,
    Stage2Error,
    Stage2ReferenceCorpus,
    Stage2TrainingManifest,
    build_stage2_reference_corpus,
    complete_stage2_reference_audit,
    decisions_path_for,
    freeze_stage2_dataset,
    freeze_stage2_split,
    load_frozen_rows,
    load_human_attestation,
    load_stage2_config,
    package_versions,
    prepare_stage2_reference_audit,
    validate_reference_plan_text,
    validate_stage2_reference_audit,
)
from sable_ir.stage2_local import (
    EvalKind,
    GenerationStatus,
    LocalGeneration,
    RawOutcome,
    Role,
    Stage1Concision,
    Stage2PlanAudit,
    _cell_metrics,
    build_stage2_eval_report,
    evaluate_stage2_eval,
    load_eval_manifest,
    model_floor_recommendation,
    prepare_stage2_eval,
    prepare_stage2_plan_audit,
    run_stage2_eval,
    select_stage2_checkpoint,
)
from sable_ir.stage2_train import (
    CheckpointRecord,
    Stage2TrainingResult,
    assert_only_language_lora_trainable,
    pad_batch,
    select_lora_targets,
    tokenize_rows,
)

SOURCE_ROOT = Path(__file__).resolve().parents[1]
DECISION_FLAGS = (
    "source_trust_sink_guard_order_effect_complete",
    "family_specific_distinction_correct",
    "applicable_clause_coverage_complete",
    "irrelevant_clauses_excluded",
    "structured_freeform_semantically_equivalent",
    "ab_policy_information_equivalent",
    "inferable_from_visible_inputs_only",
    "audited_without_test_split_outcomes",
)


def _copy_repo(tmp_path: Path, **config_overrides: Any) -> tuple[Path, Path]:
    """Copy tasks, config, and authored plans into an isolated repository root."""
    root = tmp_path / "repo"
    shutil.copytree(SOURCE_ROOT / "tasks", root / "tasks")
    (root / "data" / "stage2").mkdir(parents=True)
    shutil.copy(
        SOURCE_ROOT / "data" / "stage2" / "reference-plans.json",
        root / "data" / "stage2" / "reference-plans.json",
    )
    raw = tomllib.loads((SOURCE_ROOT / "config" / "stage2.toml").read_text(encoding="utf-8"))
    for key, value in config_overrides.items():
        section, _, leaf = key.partition(".")
        if leaf:
            raw[section][leaf] = value
        else:
            raw[section] = value
    config = Stage2Config.model_validate(raw)
    config_path = root / "config" / "stage2.toml"
    config_path.parent.mkdir()
    config_path.write_text(_to_toml(config.model_dump(mode="json")), encoding="utf-8")
    return root, config_path


def _to_toml(data: dict[str, Any]) -> str:
    def fmt(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int | float):
            return repr(value)
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, list):
            return "[" + ", ".join(fmt(item) for item in value) + "]"
        raise TypeError(type(value))

    lines: list[str] = []
    tables: list[tuple[str, dict[str, Any]]] = []
    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        else:
            lines.append(f"{key} = {fmt(value)}")
    for name, table in tables:
        lines.append(f"\n[{name}]")
        for key, value in table.items():
            lines.append(f"{key} = {fmt(value)}")
    return "\n".join(lines) + "\n"


def _complete_reference_audit(root: Path, config_path: Path) -> None:
    config = load_stage2_config(config_path)
    decisions_file = root / decisions_path_for(config)
    decisions = ReferencePlanDecisions.model_validate_json(
        decisions_file.read_text(encoding="utf-8")
    )
    filled = decisions.model_copy(
        update={
            "reviewer": "test-reviewer",
            "completed_at": datetime.now(UTC).isoformat(),
            "decisions": tuple(
                item.model_copy(update=dict.fromkeys(DECISION_FLAGS, True))
                for item in decisions.decisions
            ),
            "paraphrases": tuple(
                item.model_copy(update={"preserves_meaning": True})
                for item in decisions.paraphrases
            ),
        }
    )
    decisions_file.write_text(filled.model_dump_json(indent=2) + "\n", encoding="utf-8")
    summary = complete_stage2_reference_audit(config_path, root)
    assert summary.ready_for_freeze
    # 5 surface paraphrases + 5 tasks x 2 policies wording paraphrases.
    assert summary.paraphrase_rows == 15 and summary.passed_paraphrase_rows == 15


def _run_data_track(root: Path, config_path: Path) -> Path:
    freeze_stage2_split(config_path, root)
    build_stage2_reference_corpus(config_path, root)
    prepare_stage2_reference_audit(config_path, root)
    _complete_reference_audit(root, config_path)
    dataset_dir = root / "artifacts" / "stage2" / "dataset"
    freeze_stage2_dataset(config_path, root, dataset_dir)
    return dataset_dir


class TestConfigAndPlans:
    def test_repo_config_is_pilot_amd64_language_only(self) -> None:
        config = load_stage2_config(SOURCE_ROOT / "config" / "stage2.toml")
        assert config.design_mode.value == "pilot"
        assert config.sandbox.platform == "linux/amd64"
        assert "language_model" in config.qlora.target_modules_regex
        assert config.model.active_model_id == "Qwen/Qwen3.5-4B"
        # Both hosts are supported by the schema; this run executes on WSL2 Linux.
        assert config.hardware.operating_system in {"Windows", "Linux"}

    def test_full_design_requires_twelve_six_six(self, tmp_path: Path) -> None:
        with pytest.raises(Exception, match="full design requires"):
            _copy_repo(tmp_path, design_mode="full")

    def test_reference_plan_text_rules(self) -> None:
        good = "SOURCE: a\nTRUST: b\nSINK: c\nGUARD: d\nORDER: e\nEFFECT: f\nEND_PLAN"
        validate_reference_plan_text(good, Stage1PlanFormat.STRUCTURED)
        with pytest.raises(ValueError, match="six canonical fields"):
            validate_reference_plan_text(
                "SOURCE: a\nSINK: c\nEND_PLAN", Stage1PlanFormat.STRUCTURED
            )
        with pytest.raises(ValueError, match="field labels"):
            validate_reference_plan_text(good, Stage1PlanFormat.FREEFORM)
        with pytest.raises(ValueError, match="clause numbers"):
            validate_reference_plan_text("Apply clause 2.\nEND_PLAN", Stage1PlanFormat.FREEFORM)
        with pytest.raises(ValueError, match="END_PLAN"):
            validate_reference_plan_text("no terminator", Stage1PlanFormat.FREEFORM)


class TestDataTrack:
    def test_split_corpus_audit_and_freeze(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        dataset_dir = _run_data_track(root, config_path)
        config = load_stage2_config(config_path)
        corpus = Stage2ReferenceCorpus.model_validate_json(
            (root / config.reference_corpus_path).read_text(encoding="utf-8")
        )
        # 5 tasks x 2 policies x 2 formats x 2 surfaces x 3 orders x 2 wordings.
        assert len(corpus.rows) == 240
        assert {row.applicable_clause_position for row in corpus.rows} >= {1, 2}
        manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["files"]["train"]["rows"] == 144
        assert manifest["files"]["dev"]["rows"] == 48
        assert manifest["files"]["test"]["rows"] == 48
        assert manifest["design_mode"] == "pilot"
        train_ids = {row.base_task_id for row in load_frozen_rows(dataset_dir / "train.jsonl")}
        test_ids = {row.base_task_id for row in load_frozen_rows(dataset_dir / "test.jsonl")}
        assert not train_ids & test_ids
        for row in load_frozen_rows(dataset_dir / "train.jsonl"):
            assert "FORMAT: " in row.prompt and row.completion.endswith("END_PLAN\n")
        # LF-only bytes so Windows and POSIX hashes agree.
        assert b"\r\n" not in (dataset_dir / "train.jsonl").read_bytes()
        assert b"\r\n" not in (root / config.reference_corpus_path).read_bytes()

    def test_freeze_refuses_incomplete_audit_and_overwrites(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        freeze_stage2_split(config_path, root)
        build_stage2_reference_corpus(config_path, root)
        prepare_stage2_reference_audit(config_path, root)
        summary = validate_stage2_reference_audit(config_path, root)
        assert not summary.ready_for_freeze
        with pytest.raises(Stage2Error, match="reviewer"):
            freeze_stage2_dataset(config_path, root, tmp_path / "dataset")
        with pytest.raises(Stage2Error, match="refusing to overwrite"):
            freeze_stage2_split(config_path, root)

    def test_task_change_after_split_is_detected(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        freeze_stage2_split(config_path, root)
        task = root / "tasks" / "ssrf_redirect" / "task.json"
        task.write_text(task.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with pytest.raises(Stage2Error, match="changed after the split"):
            build_stage2_reference_corpus(config_path, root)


class FakeTokenizer:
    """Whitespace tokenizer with a Qwen-shaped chat template."""

    eos_token = "<|im_end|>"
    pad_token_id: int | None = 0

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {"<pad>": 0}

    def apply_chat_template(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        assert kwargs.get("enable_thinking") is False
        return f"<|im_start|>user\n{messages[0]['content']}<|im_end|>\n<|im_start|>assistant\n"

    def __call__(self, text: str, **kwargs: Any) -> dict[str, list[int]]:
        ids = [self.vocab.setdefault(token, len(self.vocab)) for token in text.split()]
        return {"input_ids": ids}


class TestTraining:
    def test_tokenize_rows_masks_prompt_only(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        dataset_dir = _run_data_track(root, config_path)
        rows = load_frozen_rows(dataset_dir / "dev.jsonl")[:3]
        tokenizer = FakeTokenizer()
        tokenized = tokenize_rows(rows, tokenizer, max_length=4096)
        for row, item in zip(rows, tokenized, strict=True):
            prefix_len = sum(label == -100 for label in item["labels"])
            assert prefix_len > 0
            assert item["labels"][prefix_len:] == item["input_ids"][prefix_len:]
            completion_tokens = (row.completion.rstrip("\n") + tokenizer.eos_token).split()
            assert len(item["input_ids"]) - prefix_len == len(completion_tokens)
        with pytest.raises(Stage2Error, match="truncation is forbidden"):
            tokenize_rows(rows, tokenizer, max_length=16)
        batch = pad_batch(tokenized, pad_token_id=0)
        longest = max(len(item["input_ids"]) for item in tokenized)
        assert all(len(ids) == longest for ids in batch["input_ids"])
        assert all(len(mask) == longest for mask in batch["attention_mask"])
        assert all(labels[-1] in {-100, *labels} for labels in batch["labels"])

    def test_lora_targets_language_model_only(self) -> None:
        config = load_stage2_config(SOURCE_ROOT / "config" / "stage2.toml")
        names: list[str] = ["model.visual.blocks.0.attn.qkv", "model.visual.merger.linear_fc1"]
        for layer in range(32):
            base = f"model.language_model.layers.{layer}"
            if layer % 4 == 3:
                names += [f"{base}.self_attn.{p}" for p in ("q_proj", "k_proj", "v_proj", "o_proj")]
            else:
                names += [
                    f"{base}.linear_attn.{p}"
                    for p in ("in_proj_qkv", "in_proj_z", "in_proj_a", "in_proj_b", "out_proj")
                ]
                names.append(f"{base}.linear_attn.conv1d")
            names += [f"{base}.mlp.{p}" for p in ("gate_proj", "up_proj", "down_proj")]
        names += ["model.language_model.embed_tokens", "lm_head"]
        targets = select_lora_targets(names, config.qlora.target_modules_regex)
        assert len(targets) == 8 * 4 + 24 * 3 + 32 * 3
        assert all("language_model" in name for name in targets)
        assert not any("visual" in name or "in_proj_a" in name for name in targets)
        with pytest.raises(Stage2Error, match="matched only"):
            select_lora_targets(names[:5], config.qlora.target_modules_regex)
        assert_only_language_lora_trainable(
            ["base_model.model.model.language_model.layers.0.mlp.up_proj.lora_A.default.weight"]
        )
        with pytest.raises(Stage2Error, match="non-planner or non-LoRA"):
            assert_only_language_lora_trainable(["base_model.model.model.visual.blocks.0.weight"])


class FakeGenerator:
    """Planner marks its (task, policy); renderer returns the matching reference implementation."""

    def __init__(self, root: Path, documents: dict[str, tuple[str, PolicyValue]]) -> None:
        self.root = root
        self.documents = documents
        self.calls: list[Role] = []

    def generate(
        self, prompt: str, *, role: Role, max_new_tokens: int, seed: int
    ) -> LocalGeneration:
        self.calls.append(role)
        if role is Role.PLANNER:
            task_id, policy = next(
                value for document, value in self.documents.items() if document in prompt
            )
            marker = f"task={task_id} policy={policy.value}"
            if "FORMAT: STRUCTURED" in prompt:
                text = (
                    f"SOURCE: input\nTRUST: untrusted\nSINK: sink\nGUARD: {marker}\n"
                    "ORDER: check first\nEFFECT: result\nEND_PLAN"
                )
            else:
                text = f"Guard the sink; {marker}.\nEND_PLAN"
        else:
            match = re.search(r"task=(\w+) policy=([AB])", prompt)
            if match:
                task_id, policy_value = match.group(1), match.group(2)
            else:
                # Direct conditions: the original-benchmark prompt names a different function,
                # so fall back to the run's task when no surface signature matches.
                known = {task for task, _policy in self.documents.values()}
                task_id = next(
                    (name for name in sorted(known) if _signature(name) in prompt),
                    sorted(known)[0],
                )
                policy_value = "A"
            source = (
                self.root / "tasks" / task_id / f"reference_{policy_value.lower()}.py"
            ).read_text(encoding="utf-8")
            text = f"```python\n{source}\n```"
        return LocalGeneration(
            text=text,
            prompt_tokens=len(prompt.split()),
            output_tokens=len(text.split()),
            finish_reason="stop",
            latency_seconds=0.01,
            seed=seed,
        )

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def describe(self) -> dict[str, str]:
        return {"backend": "fake"}


def _signature(task_id: str) -> str:
    return {
        "path_symlink_report": "read_report(",
        "path_symlink_archive": "extract_tar_to_path(",
        "sql_identifier": "fetch_rows(",
        "command_executable": "run_text_utility(",
        "ssrf_redirect": "fetch_text(",
    }[task_id]


def _fake_training_result(root: Path, run_id: str, steps: tuple[int, ...]) -> Path:
    from sable_ir.stage2_train import hash_tree

    checkpoints = []
    output = root / "artifacts" / "stage2" / "training" / run_id / "checkpoints"
    for step in steps:
        directory = output / f"checkpoint-{step}"
        directory.mkdir(parents=True)
        (directory / "adapter_config.json").write_text('{"r": 32}\n', encoding="utf-8")
        (directory / "adapter_model.safetensors").write_bytes(b"adapter-%d" % step)
        checkpoints.append(
            CheckpointRecord(
                directory=directory.relative_to(root).as_posix(),
                global_step=step,
                epoch=float(steps.index(step) + 1),
                adapter_file_sha256s=hash_tree(directory, adapter_only=True),
            )
        )
    final = output / "final-adapter-unselected"
    final.mkdir()
    (final / "adapter_model.safetensors").write_bytes(b"final")
    result = Stage2TrainingResult(
        run_id=run_id,
        started_at="2026-09-04T00:00:00+00:00",
        finished_at="2026-09-04T01:00:00+00:00",
        training_manifest_sha256="0" * 64,
        model_id="Qwen/Qwen3.5-4B",
        revision="851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        architecture="Qwen3_5ForConditionalGeneration",
        checkpoints=tuple(checkpoints),
        final_adapter_directory=final.relative_to(root).as_posix(),
        final_adapter_file_sha256s=hash_tree(final),
        trainable_parameter_names_sha256="1" * 64,
        lora_target_module_count=200,
        trainable_parameters=1,
        total_parameters=2,
        trainable_fraction=0.5,
        train_rows=144,
        dev_rows=48,
        max_train_sequence_tokens=900,
        train_log_history=(),
        peak_gpu_memory_gib=9.5,
    )
    path = output.parent / "training-result.json"
    path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    config = load_stage2_config(root / "config" / "stage2.toml")
    manifest = Stage2TrainingManifest(
        run_id=run_id,
        created_at="2026-09-04T00:00:00+00:00",
        config_path="config/stage2.toml",
        config_sha256="2" * 64,
        dataset_manifest_path="artifacts/stage2/dataset/manifest.json",
        dataset_manifest_sha256="3" * 64,
        preflight_path=f"artifacts/stage2/training/{run_id}/preflight.json",
        preflight_sha256="4" * 64,
        model_canary_path="artifacts/stage2/canary/canary.json",
        model_canary_sha256="5" * 64,
        stage1_report_sha256=None,
        stage1_gate_status_at_authorization=Stage1GateStatus.PENDING,
        stage1_gate_override="pilot started before Stage 1 finished",
        model=config.model,
        qlora=config.qlora,
        package_versions={"torch": "2.9.1+cu128"},
        gpu_name="NVIDIA GeForce RTX 5080",
        gpu_total_memory_gib=15.92,
        cuda_version="runtime=12.8; driver=580.0",
        output_directory=output.relative_to(root).as_posix(),
    )
    (output.parent / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return path


class TestLocalEval:
    def test_dev_run_report_audit_and_selection(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(
            tmp_path,
            **{
                "generation.plans_per_cell": 1,
                "generation.renders_per_plan": 1,
                "generation.direct_samples_per_condition": 1,
                "generation.concision_levels": ["full"],
            },
        )
        freeze_stage2_split(config_path, root)
        training_result = _fake_training_result(root, "train-01", (18, 36))
        reports: list[Path] = []
        for step in (18, 36):
            run_dir = root / "artifacts" / "stage2" / "eval" / f"dev-{step}"
            manifest = prepare_stage2_eval(
                config_path,
                root,
                run_dir,
                f"dev-{step}",
                EvalKind.DEV_SELECTION,
                adapter_directory=root
                / "artifacts"
                / "stage2"
                / "training"
                / "train-01"
                / "checkpoints"
                / f"checkpoint-{step}",
                training_result_path=training_result,
            )
            assert [t.task_id for t in manifest.tasks] == ["ssrf_redirect"]
            assert len(manifest.plan_jobs) == 4 and len(manifest.render_jobs) == 4
            assert len(manifest.direct_jobs) == 6
            assert manifest.planner_adapter is not None
            assert manifest.planner_adapter.global_step == step
            documents = {}
            for job in manifest.plan_jobs:
                request = json.loads((run_dir / job.request_path).read_text(encoding="utf-8"))
                documents[request["safety_document"]] = (job.task_id, job.assigned_policy)
            generator = FakeGenerator(root, documents)
            summary = run_stage2_eval(run_dir / "manifest.json", generator)
            assert summary.plans_complete == 4 and summary.renders_complete == 4
            assert summary.direct_complete == 6
            # Resumable: a second pass generates nothing new.
            again = run_stage2_eval(run_dir / "manifest.json", generator)
            assert again.plans_complete == 4 and generator.calls.count(Role.PLANNER) == 4
            config = load_stage2_config(config_path)
            evaluation = evaluate_stage2_eval(
                run_dir / "manifest.json", root, UnsafeLocalSandbox(config.sandbox)
            )
            assert evaluation.evaluated == 10 and evaluation.without_candidate == 0
            audit_path = run_dir / "plan-audit.json"
            audit = prepare_stage2_plan_audit(run_dir / "manifest.json", root, audit_path)
            assert len(audit.rows) == 4 and audit.reviewer is None
            completed = audit.model_copy(
                update={
                    "reviewer": "test-reviewer",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "rows": tuple(
                        row.model_copy(
                            update={
                                "audited_without_generated_code": True,
                                "clause_selection": ClauseSelection.CORRECT,
                                "policy_visibility": PolicyVisibility.PRESERVED,
                                "selected_clause_ids": row.applicable_clause_ids,
                                "irrelevant_clause_ids_included": (),
                                "confidence": AuditConfidence.CONFIDENT,
                            }
                        )
                        for row in audit.rows
                    ),
                }
            )
            audit_path.write_text(completed.model_dump_json(indent=2) + "\n", encoding="utf-8")
            Stage2PlanAudit.model_validate_json(audit_path.read_text(encoding="utf-8"))
            report_path = run_dir / "report.json"
            report = build_stage2_eval_report(
                run_dir / "manifest.json", root, report_path, plan_audit_path=audit_path
            )
            assert report.complete and report.pilot and report.kind is EvalKind.DEV_SELECTION
            assert report.splits_used == (SplitName.DEV,)
            assert report.selection_metric_value == 1.0
            assert not report.invalid_task_or_tests
            cell = report.by_format_and_concision["structured/full"]
            assert cell.assigned_policy_and_functional_rate == 1.0
            assert cell.policy_controllability == 1.0
            assert cell.visible_retention_rate == 1.0
            assert cell.false_certificate_rate == 0.0
            direct = report.direct_by_condition
            assert direct["full_document_a"].assigned_policy_and_functional_rate == 1.0
            assert direct["full_document_b"].assigned_policy_and_functional_rate == 0.0
            assert report.model_floor.recommendation == "not_a_model_floor_run"
            assert report.bottleneck_sanity.full_structured_plan_functional == 1.0
            # No Stage 1 report exists in this repo copy: results stay provisional.
            assert report.stage1_gate is Stage1GateStatus.PENDING
            assert report.stage2_status == "provisional_pending_stage1"
            assert report.training_stage1_gate_override == "pilot started before Stage 1 finished"
            reports.append(report_path)
        selection = select_stage2_checkpoint(
            reports, training_result, root / "artifacts" / "stage2" / "selection.json"
        )
        assert selection.selected_adapter.global_step == 18  # tie -> earliest step
        assert selection.candidates == {
            "artifacts/stage2/training/train-01/checkpoints/checkpoint-18": 1.0,
            "artifacts/stage2/training/train-01/checkpoints/checkpoint-36": 1.0,
        }
        test_dir = root / "artifacts" / "stage2" / "eval" / "test-final"
        with pytest.raises(Stage2Error, match="dev-selected checkpoint"):
            prepare_stage2_eval(
                config_path,
                root,
                test_dir,
                "test-final",
                EvalKind.TEST_FINAL,
                adapter_directory=root
                / "artifacts/stage2/training/train-01/checkpoints/checkpoint-36",
                training_result_path=training_result,
                checkpoint_selection_path=root / "artifacts" / "stage2" / "selection.json",
            )
        final = prepare_stage2_eval(
            config_path,
            root,
            test_dir,
            "test-final",
            EvalKind.TEST_FINAL,
            adapter_directory=root / "artifacts/stage2/training/train-01/checkpoints/checkpoint-18",
            training_result_path=training_result,
            checkpoint_selection_path=root / "artifacts" / "stage2" / "selection.json",
        )
        assert [t.task_id for t in final.tasks] == ["path_symlink_archive"]
        assert final.checkpoint_selection_sha256 is not None

    def test_model_floor_rule_three_way(self) -> None:
        assert model_floor_recommendation(0.5, 0.4, 0.3)[1] == "continue_with_primary_model"
        assert model_floor_recommendation(0.2, 0.4, 0.3)[1] == "move_to_fallback_model"
        assert model_floor_recommendation(0.5, 0.1, 0.3)[1] == "stop_or_pivot"
        assert model_floor_recommendation(0.2, 0.1, 0.3)[1] == "move_to_fallback_model"
        assert model_floor_recommendation(0.3, 0.3, 0.3)[0] is True

    def test_stage1_gate_status_drives_stage2_status(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        freeze_stage2_split(config_path, root)
        config = load_stage2_config(config_path)
        report_path = root / config.stage1_report_path
        report_path.parent.mkdir(parents=True)
        report_path.write_text('{"recommendation": "continue_to_stage2"}', encoding="utf-8")
        run_dir = root / "artifacts" / "stage2" / "eval" / "gate"
        prepare_stage2_eval(
            config_path,
            root,
            run_dir,
            "gate",
            EvalKind.DEV_SELECTION,
            adapter_directory=None,
            training_result_path=None,
        )
        passed = build_stage2_eval_report(run_dir / "manifest.json", root, run_dir / "r1.json")
        assert passed.stage2_status == "valid_continuation"
        report_path.write_text('{"recommendation": "stop"}', encoding="utf-8")
        failed = build_stage2_eval_report(run_dir / "manifest.json", root, run_dir / "r2.json")
        assert failed.stage1_gate is Stage1GateStatus.FAILED
        assert failed.stage2_status == "exploratory_stage1_failed"

    def test_model_floor_covers_train_and_dev_only(self, tmp_path: Path) -> None:
        root, config_path = _copy_repo(tmp_path)
        freeze_stage2_split(config_path, root)
        run_dir = root / "artifacts" / "stage2" / "eval" / "floor"
        manifest = prepare_stage2_eval(
            config_path,
            root,
            run_dir,
            "floor",
            EvalKind.MODEL_FLOOR,
            adapter_directory=None,
            training_result_path=None,
        )
        # Train + dev only: the floor sets model selection, so the test task stays held out.
        assert len(manifest.tasks) == 4 and manifest.planner_adapter is None
        assert SplitName.TEST not in {task.split for task in manifest.tasks}
        # Planner-independent arms only.
        assert manifest.plan_jobs == ()
        assert manifest.render_jobs == ()
        assert len(manifest.direct_jobs) == 4 * 2 * 4
        assert len(manifest.reference_render_jobs) == 4 * 2 * 2 * 4
        assert load_eval_manifest(run_dir / "manifest.json") == manifest
        report = build_stage2_eval_report(run_dir / "manifest.json", root, run_dir / "r.json")
        assert not report.complete
        assert report.model_floor.recommendation == "incomplete"
        training_result = _fake_training_result(root, "train-02", (18,))
        with pytest.raises(Stage2Error, match="dev_selection reports only"):
            select_stage2_checkpoint([run_dir / "r.json"], training_result, tmp_path / "sel.json")


def test_dataset_freeze_refuses_a_split_frozen_under_another_config(
    tmp_path: Path,
) -> None:
    """A Stage 2 config change must invalidate the frozen split, not pass silently."""
    root = Path.cwd()
    config_path = root / "config/stage2.toml"
    split = json.loads((root / "data/stage2/split.json").read_text())
    assert split["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()

    mutated = tmp_path / "stage2-mutated.toml"
    mutated.write_text(
        config_path.read_text().replace('min_total_vram_gib = 15.0', 'min_total_vram_gib = 14.0')
    )
    with pytest.raises(Stage2Error, match="records a different Stage 2 config"):
        freeze_stage2_dataset(mutated, root, tmp_path / "dataset")


def test_training_version_guard_round_trips_non_distribution_keys() -> None:
    """package_versions records the interpreter, which is not a distribution name.

    The training guard must verify with the same function that froze the manifest; re-deriving
    each recorded key via importlib.metadata reports "absent" for `python` and aborts every run.
    """
    versions = package_versions()
    assert versions["python"] == platform.python_version()
    assert versions == package_versions()
    with pytest.raises(importlib.metadata.PackageNotFoundError):
        importlib.metadata.version("python")


def test_model_floor_gate_is_independent_of_the_trained_planner() -> None:
    """Proposal II.B.6: both floor arms must be planner-independent.

    Arm 2 is the audited reference plan into the adapter-disabled renderer. Feeding
    trained-planner plans in would conflate planner quality with renderer capability, which
    II.B.6.3 warns against ("do not interpret a weak renderer as evidence that the intermediate
    language failed"). A perfect trained planner must not rescue a failing reference arm.
    """
    passed, recommendation, rationale = model_floor_recommendation(0.9, 0.1, 0.30)
    assert passed is False
    assert recommendation == "stop_or_pivot"
    assert "reference plan" in rationale
    assert "plan channel" in rationale

    # Direct below the floor selects the larger model regardless of the plan arm.
    passed, recommendation, _ = model_floor_recommendation(0.1, 0.9, 0.30)
    assert recommendation == "move_to_fallback_model"

    passed, recommendation, _ = model_floor_recommendation(0.5, 0.5, 0.30)
    assert passed is True and recommendation == "continue_with_primary_model"


def test_model_floor_never_touches_the_held_out_test_task(tmp_path: Path) -> None:
    """The floor sets the 4B-vs-9B decision, so the test task must not appear in it.

    It must also carry no trained-planner jobs: those are checkpoint-selection diagnostics.
    """
    root = Path.cwd()
    run_directory = tmp_path / "floor-clean"
    manifest = prepare_stage2_eval(
        root / "config/stage2.toml",
        root,
        run_directory,
        "floor-clean",
        EvalKind.MODEL_FLOOR,
        adapter_directory=None,
        training_result_path=None,
    )
    splits = {task.split for task in manifest.tasks}
    assert SplitName.TEST not in splits
    assert splits == {SplitName.TRAIN, SplitName.DEV}
    assert "path_symlink_archive" not in {task.task_id for task in manifest.tasks}

    # planner-independent only
    assert manifest.plan_jobs == ()
    assert manifest.render_jobs == ()
    # 4 tasks x 2 policies x 4 renders
    assert len(manifest.direct_jobs) == 32
    assert {j.condition for j in manifest.direct_jobs} == {
        Stage0Condition.FULL_DOCUMENT_A,
        Stage0Condition.FULL_DOCUMENT_B,
    }
    # 4 tasks x 2 policies x 2 formats x 4 renders
    assert len(manifest.reference_render_jobs) == 64


class TestFloorDenominatorRule:
    """A truncated completed output is a model failure; a missing job is incompleteness."""

    @staticmethod
    def _ref_row(fmt: Stage1PlanFormat, *, attempted: bool, evaluated: bool, passed: bool):
        from sable_ir.stage2_local import ReferenceRenderRow

        outcome = RawOutcome.PASS if passed else RawOutcome.NOT_RUN
        return ReferenceRenderRow(
            job_id=f"t__A__{fmt.value}__reference__r00",
            task_id="t",
            split=SplitName.TRAIN,
            assigned_policy=PolicyValue.A,
            plan_format=fmt,
            render_index=0,
            status=(
                GenerationStatus.GENERATED
                if evaluated
                else GenerationStatus.LENGTH
                if attempted
                else GenerationStatus.SKIPPED_MALFORMED_PLAN
            ),
            attempted=attempted,
            evaluated=evaluated,
            compilation=outcome,
            functionality=outcome,
            policy_a=outcome,
            policy_b=RawOutcome.NOT_RUN,
            original_security=RawOutcome.NOT_RUN,
            functional=passed,
            assigned_policy_and_functional=passed,
        )

    def test_truncated_completed_output_counts_as_failure_in_the_denominator(self) -> None:
        rows = [
            self._ref_row(Stage1PlanFormat.STRUCTURED, attempted=True, evaluated=True, passed=True)
            for _ in range(19)
        ]
        # three truncations: generated a completed outcome, produced no candidate
        rows += [
            self._ref_row(
                Stage1PlanFormat.STRUCTURED, attempted=True, evaluated=False, passed=False
            )
            for _ in range(3)
        ]
        scored = [bool(r.assigned_policy_and_functional) for r in rows if r.attempted]
        assert len(scored) == 22, "truncations must stay in the denominator"
        assert sum(scored) == 19
        # Excluding them would inflate 19/22 to 19/19.
        inflated = [bool(r.assigned_policy_and_functional) for r in rows if r.evaluated]
        assert len(inflated) == 19
        assert sum(scored) / len(scored) < sum(inflated) / len(inflated)

    def test_missing_job_is_incompleteness_not_a_failure(self) -> None:
        rows = [
            self._ref_row(Stage1PlanFormat.STRUCTURED, attempted=True, evaluated=True, passed=True),
            # no result file at all: never attempted
            self._ref_row(
                Stage1PlanFormat.STRUCTURED, attempted=False, evaluated=False, passed=False
            ),
        ]
        scored = [bool(r.assigned_policy_and_functional) for r in rows if r.attempted]
        assert len(scored) == 1, "a missing job must not be scored as a failure"


class TestMetricSpecificDenominators:
    """Truncations count against unconditional metrics but not conditional ones."""

    @staticmethod
    def _row(*, attempted: bool, functional: bool, policy_pass: bool, visible: bool | None = None):
        from sable_ir.stage2_local import RenderRow

        ok = RawOutcome.PASS
        no = RawOutcome.FAIL if attempted else RawOutcome.NOT_RUN
        return RenderRow(
            job_id="j",
            plan_job_id="p",
            task_id="t",
            split=SplitName.TRAIN,
            assigned_policy=PolicyValue.A,
            plan_format=Stage1PlanFormat.STRUCTURED,
            concision=Stage1Concision.FULL,
            plan_sample_index=0,
            render_index=0,
            plan_status=GenerationStatus.GENERATED,
            plan_tokens=100,
            document_tokens=400,
            length_bin="64-128",
            render_status=GenerationStatus.GENERATED if functional else GenerationStatus.LENGTH,
            attempted=attempted,
            evaluated=attempted and functional,
            compilation=ok if functional else no,
            functionality=ok if functional else no,
            policy_a=ok if policy_pass else no,
            policy_b=no,
            original_security=no,
            functional=functional,
            assigned_policy_pass=policy_pass,
            assigned_policy_and_functional=functional and policy_pass,
            opposite_policy_and_functional=False,
            passes_both_policies=False,
            visible_policy_retained=visible,
            clause_selection=None,
            false_certificate=None,
            confident_wrong_clause_and_assigned_failure=None,
        )

    def test_truncations_cannot_inflate_unconditional_frontier_values(self) -> None:
        good = [self._row(attempted=True, functional=True, policy_pass=True) for _ in range(6)]
        trunc = [self._row(attempted=True, functional=False, policy_pass=False) for _ in range(6)]
        clean = _cell_metrics(good)
        mixed = _cell_metrics(good + trunc)
        assert clean.functional_rate == 1.0
        assert mixed.functional_rate == 0.5, "truncations must halve the functional rate"
        assert mixed.assigned_policy_and_functional_rate == 0.5
        assert mixed.attempted_rows == 12 and mixed.evaluated_rows == 6

    def test_heavy_truncation_cannot_look_equal_to_complete_yield(self) -> None:
        complete = _cell_metrics(
            [self._row(attempted=True, functional=True, policy_pass=True) for _ in range(8)]
        )
        truncating = _cell_metrics(
            [self._row(attempted=True, functional=True, policy_pass=True) for _ in range(2)]
            + [self._row(attempted=True, functional=False, policy_pass=False) for _ in range(6)]
        )
        assert complete.assigned_policy_and_functional_rate == 1.0
        assert truncating.assigned_policy_and_functional_rate == 0.25
        assert (
            truncating.assigned_policy_and_functional_rate
            < complete.assigned_policy_and_functional_rate
        )

    def test_conditional_metrics_keep_their_conditioning(self) -> None:
        rows = [
            self._row(attempted=True, functional=True, policy_pass=True),
            self._row(attempted=True, functional=True, policy_pass=False),
            # truncated: not functional, so it must not enter conditional compliance
            self._row(attempted=True, functional=False, policy_pass=False),
        ]
        m = _cell_metrics(rows)
        assert m.assigned_policy_pass_rate == 0.5, "conditioned on the 2 functional outputs"
        assert m.assigned_policy_and_functional_rate == pytest.approx(1 / 3, abs=1e-4), (
            "unconditional: rates are rounded to 4dp"
        )
        assert m.functional_rows == 2 and m.attempted_rows == 3

    def test_plan_visibility_is_independent_of_rendering(self) -> None:
        rows = [
            self._row(attempted=True, functional=True, policy_pass=True, visible=True),
            # audited plan whose render truncated: visibility is still a property of the plan
            self._row(attempted=True, functional=False, policy_pass=False, visible=True),
        ]
        assert _cell_metrics(rows).visible_retention_rate == 1.0


class TestHumanAttestation:
    """Human sign-off is append-only: it binds audited bytes without rewriting provenance."""

    def test_attestation_binds_the_exact_audited_bytes(self) -> None:
        root = Path.cwd()
        attestation = load_human_attestation(
            root / "data/stage2/reference-audit.human-attestation.json", root
        )
        assert attestation.reviewer == "Meghana Indukuri"
        # Claude's preliminary provenance survives alongside the human sign-off.
        assert "Claude" in attestation.preliminary_reviewer
        audit = json.loads((root / "data/stage2/reference-audit.json").read_text())
        assert "PRELIMINARY" in audit["reviewer"] and "Claude" in audit["reviewer"]

    def test_changed_audit_content_invalidates_the_attestation(self, tmp_path: Path) -> None:
        """Approving unchanged data is metadata; changing the data must void the sign-off."""
        root = tmp_path / "repo"
        shutil.copytree(Path.cwd() / "data", root / "data")
        # the attestation also binds the frozen dataset manifest; copy it so this test isolates
        # the audit-bytes binding rather than tripping on a missing artifact
        dataset = root / "artifacts/stage2/dataset"
        dataset.mkdir(parents=True)
        shutil.copy(
            Path.cwd() / "artifacts/stage2/dataset/manifest.json", dataset / "manifest.json"
        )
        att_path = root / "data/stage2/reference-audit.human-attestation.json"
        audit_path = root / "data/stage2/reference-audit.json"
        # unchanged content: the attestation still binds
        load_human_attestation(att_path, root)
        # a single changed audit decision voids it
        audit = json.loads(audit_path.read_text())
        flag = "inferable_from_visible_inputs_only"
        audit["rows"][0][flag] = not audit["rows"][0][flag]
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        with pytest.raises(Stage2Error, match="different audit bytes"):
            load_human_attestation(att_path, root)


def test_pending_attestation_does_not_satisfy_a_human_review_gate(tmp_path: Path) -> None:
    """A named reviewer who has not inspected the current bytes is not completed review."""
    root = Path.cwd()
    path = root / "data/stage2/reference-audit.human-attestation.json"
    attestation = load_human_attestation(path, root)
    pending = attestation.model_copy(update={"decision": "pending_human_review"})
    approved = attestation.model_copy(update={"decision": "approved_after_applied_corrections"})
    assert pending.approved is False
    assert approved.approved is True
    # the reviewer name is still recorded either way; only the decision gates
    assert pending.reviewer == approved.reviewer
