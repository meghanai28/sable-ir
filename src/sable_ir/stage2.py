"""Stage 2 immutable data, split, preflight, and training-manifest utilities."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import tomllib
from collections import Counter
from contextlib import suppress
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, TypeVar

from pydantic import Field, ValidationError, model_validator

from sable_ir.config import ConfigLoadError
from sable_ir.schema import PolicyValue, Stage1PlanFormat, StrictModel

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Revision = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)
STRUCTURED_FIELDS = ("SOURCE", "TRUST", "SINK", "GUARD", "ORDER", "EFFECT")
TRAINING_HARNESS_VERSION: Literal["stage2-qlora-training-v1"] = (
    "stage2-qlora-training-v1"
)
DATASET_HARNESS_VERSION: Literal["stage2-reference-dataset-v1"] = (
    "stage2-reference-dataset-v1"
)


class Stage2Error(ValueError):
    """Stage 2 artifact, readiness, or integrity failure."""


class SplitName(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


class Stage2ModelSpec(StrictModel):
    model_id: Literal["Qwen/Qwen3.5-4B"] = "Qwen/Qwen3.5-4B"
    revision: Revision
    fallback_model_id: Literal["Qwen/Qwen3.5-9B"] = "Qwen/Qwen3.5-9B"
    fallback_revision: Revision
    architecture: Literal["Qwen3_5ForConditionalGeneration"] = (
        "Qwen3_5ForConditionalGeneration"
    )
    auto_class: Literal["AutoModelForMultimodalLM"] = "AutoModelForMultimodalLM"
    thinking: Literal["disabled"] = "disabled"


class QLoRAConfig(StrictModel):
    load_in_4bit: Literal[True] = True
    quant_type: Literal["nf4"] = "nf4"
    double_quant: Literal[True] = True
    compute_dtype: Literal["bfloat16"] = "bfloat16"
    lora_rank: Annotated[int, Field(gt=0)] = 32
    lora_alpha: Annotated[int, Field(gt=0)] = 64
    lora_dropout: Annotated[float, Field(ge=0, lt=1)] = 0.05
    target_modules_regex: str
    max_sequence_tokens: Annotated[int, Field(ge=512)] = 4096
    epochs: Annotated[float, Field(gt=0)] = 3.0
    learning_rate: Annotated[float, Field(gt=0)] = 0.0002
    per_device_train_batch_size: Annotated[int, Field(gt=0)] = 1
    per_device_eval_batch_size: Annotated[int, Field(gt=0)] = 1
    gradient_accumulation_steps: Annotated[int, Field(gt=0)] = 16
    warmup_ratio: Annotated[float, Field(ge=0, lt=1)] = 0.03
    weight_decay: Annotated[float, Field(ge=0)] = 0.0
    seed: int = 271828
    data_seed: int = 314159
    save_strategy: Literal["epoch"] = "epoch"
    eval_strategy: Literal["epoch"] = "epoch"
    checkpoint_selection_metric: Literal["dev_assigned_policy_and_functional"] = (
        "dev_assigned_policy_and_functional"
    )


class Stage2Config(StrictModel):
    schema_version: Literal[1] = 1
    artifacts_dir: str = "artifacts/stage2"
    split_manifest_path: str
    reference_corpus_path: str
    reference_audit_path: str
    stage1_report_path: str
    required_train_tasks: Literal[12] = 12
    required_dev_tasks: Literal[6] = 6
    required_test_tasks: Literal[6] = 6
    model_floor_source_tasks: Literal[5] = 5
    model_floor_assigned_functional_min: float = Field(default=0.30, ge=0, le=1)
    expected_gpu_pattern: Literal["RTX 5090"] = "RTX 5090"
    model: Stage2ModelSpec
    qlora: QLoRAConfig

    @model_validator(mode="after")
    def validate_paths(self) -> Stage2Config:
        for name in (
            "artifacts_dir",
            "split_manifest_path",
            "reference_corpus_path",
            "reference_audit_path",
            "stage1_report_path",
        ):
            value = getattr(self, name)
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"{name} must be repository-relative and may not contain '..'")
        try:
            re.compile(self.qlora.target_modules_regex)
        except re.error as error:
            raise ValueError("qlora.target_modules_regex is not valid") from error
        return self


class SplitAssignment(StrictModel):
    base_task_id: str
    task_path: str
    split: SplitName
    family: str

    @model_validator(mode="after")
    def validate_task_path(self) -> SplitAssignment:
        path = PurePosixPath(self.task_path)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
            raise ValueError("split task_path must be a repository-relative JSON path")
        return self


class Stage2SplitManifest(StrictModel):
    schema_version: Literal[1] = 1
    status: Literal["draft", "frozen"]
    created_at: str
    assignments: tuple[SplitAssignment, ...]
    allocation_rule: Literal["base_task_before_derivation"] = "base_task_before_derivation"
    train_count_required: Literal[12] = 12
    dev_count_required: Literal[6] = 6
    test_count_required: Literal[6] = 6

    @model_validator(mode="after")
    def validate_assignments(self) -> Stage2SplitManifest:
        ids = [row.base_task_id for row in self.assignments]
        paths = [row.task_path for row in self.assignments]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise ValueError("each base task and task path may occur in exactly one split")
        counts = Counter(row.split for row in self.assignments)
        expected = {SplitName.TRAIN: 12, SplitName.DEV: 6, SplitName.TEST: 6}
        if self.status == "frozen" and counts != expected:
            raise ValueError(f"frozen Stage 2 split must contain exactly {expected}")
        return self


class ReferencePlanRow(StrictModel):
    row_id: str
    base_task_id: str
    split: SplitName
    policy: PolicyValue
    plan_format: Stage1PlanFormat
    surface_variant_id: str
    document_order_variant_id: str
    policy_wording_variant_id: str
    surface_request: str
    safety_document: str
    applicable_clause_ids: tuple[str, ...]
    irrelevant_clause_ids: tuple[str, ...]
    prompt: str
    completion: str

    @model_validator(mode="after")
    def validate_plan_representation(self) -> ReferencePlanRow:
        if not self.completion.rstrip().endswith("END_PLAN"):
            raise ValueError("every reference plan must end with END_PLAN")
        if self.plan_format is Stage1PlanFormat.STRUCTURED:
            labels = re.findall(r"(?m)^(SOURCE|TRUST|SINK|GUARD|ORDER|EFFECT)$", self.completion)
            if tuple(labels) != STRUCTURED_FIELDS:
                raise ValueError("structured plans require each canonical field exactly once")
        elif any(re.search(rf"(?m)^{field}$", self.completion) for field in STRUCTURED_FIELDS):
            raise ValueError("freeform plans may not contain structured field labels")
        return self

    @property
    def variant_key(self) -> tuple[str, SplitName, str, str, str]:
        return (
            self.base_task_id,
            self.split,
            self.surface_variant_id,
            self.document_order_variant_id,
            self.policy_wording_variant_id,
        )


class Stage2ReferenceCorpus(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    rows: tuple[ReferencePlanRow, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> Stage2ReferenceCorpus:
        if not self.rows or len({row.row_id for row in self.rows}) != len(self.rows):
            raise ValueError("reference corpus must have nonempty unique row IDs")
        return self


class ReferenceAuditRow(StrictModel):
    row_id: str
    row_sha256: Sha256
    source_trust_sink_guard_order_effect_complete: bool
    family_specific_distinction_correct: bool
    applicable_clause_coverage_complete: bool
    irrelevant_clauses_excluded: bool
    structured_freeform_semantically_equivalent: bool
    ab_policy_information_equivalent: bool
    audited_without_test_split_outcomes: Literal[True]
    notes: str | None = None

    @property
    def passed(self) -> bool:
        return all(
            (
                self.source_trust_sink_guard_order_effect_complete,
                self.family_specific_distinction_correct,
                self.applicable_clause_coverage_complete,
                self.irrelevant_clauses_excluded,
                self.structured_freeform_semantically_equivalent,
                self.ab_policy_information_equivalent,
                self.audited_without_test_split_outcomes,
            )
        )


class Stage2ReferenceAudit(StrictModel):
    schema_version: Literal[1] = 1
    corpus_sha256: Sha256
    split_manifest_sha256: Sha256
    behavior_blinded: Literal[True] = True
    reviewer: str
    completed_at: str
    rows: tuple[ReferenceAuditRow, ...]


class FrozenDatasetRow(StrictModel):
    row_id: str
    base_task_id: str
    split: SplitName
    policy: PolicyValue
    plan_format: Stage1PlanFormat
    prompt: str
    completion: str
    source_row_sha256: Sha256


class FrozenDatasetFile(StrictModel):
    path: str
    sha256: Sha256
    rows: int


class Stage2DatasetManifest(StrictModel):
    schema_version: Literal[1] = 1
    harness_version: Literal["stage2-reference-dataset-v1"] = DATASET_HARNESS_VERSION
    created_at: str
    split_manifest_sha256: Sha256
    corpus_sha256: Sha256
    audit_sha256: Sha256
    task_sha256s: dict[str, Sha256]
    files: dict[SplitName, FrozenDatasetFile]
    base_tasks_by_split: dict[SplitName, tuple[str, ...]]
    all_rows_audited_pass: Literal[True] = True


class PreflightCheck(StrictModel):
    check: str
    passed: bool
    detail: str


class Stage2PreflightReport(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    config_sha256: Sha256
    host: dict[str, str]
    checks: tuple[PreflightCheck, ...]
    ready_for_dataset_freeze: bool
    ready_for_training: bool


class Stage2TrainingManifest(StrictModel):
    schema_version: Literal[1] = 1
    harness_version: Literal["stage2-qlora-training-v1"] = TRAINING_HARNESS_VERSION
    run_id: str
    created_at: str
    config_path: str
    config_sha256: Sha256
    dataset_manifest_path: str
    dataset_manifest_sha256: Sha256
    stage1_report_sha256: Sha256
    model: Stage2ModelSpec
    qlora: QLoRAConfig
    package_versions: dict[str, str]
    gpu_name: str
    cuda_version: str
    test_split_access_during_training: Literal[False] = False
    checkpoint_selection_split: Literal["dev"] = "dev"
    renderer_adapter_enabled: Literal[False] = False
    only_planner_adapter_trainable: Literal[True] = True
    output_directory: str


def load_stage2_config(path: Path) -> Stage2Config:
    try:
        with path.open("rb") as handle:
            return Stage2Config.model_validate(tomllib.load(handle))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise ConfigLoadError(f"could not load Stage 2 config {path}: {error}") from error


def audit_stage2_preflight(
    config_path: Path, repository_root: Path, output_path: Path
) -> Stage2PreflightReport:
    """Record every PC/data prerequisite without downloading a model or touching a GPU."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    checks: list[PreflightCheck] = []
    split = _optional_model(Stage2SplitManifest, root / config.split_manifest_path)
    counts = Counter(row.split for row in split.assignments) if split else Counter()
    expected = {SplitName.TRAIN: 12, SplitName.DEV: 6, SplitName.TEST: 6}
    split_ok = split is not None and split.status == "frozen" and counts == expected
    checks.append(
        PreflightCheck(
            check="frozen_base_task_split_12_6_6",
            passed=split_ok,
            detail=f"observed={dict(counts)}; derived rows inherit their base-task split",
        )
    )
    corpus = _optional_model(Stage2ReferenceCorpus, root / config.reference_corpus_path)
    audit = _optional_model(Stage2ReferenceAudit, root / config.reference_audit_path)
    corpus_ok = corpus is not None and audit is not None
    if corpus_ok:
        assert corpus is not None and audit is not None
        corpus_ok = audit.corpus_sha256 == _sha((root / config.reference_corpus_path).read_bytes())
        corpus_ok = corpus_ok and len(audit.rows) == len(corpus.rows) and all(
            row.passed for row in audit.rows
        )
    checks.append(
        PreflightCheck(
            check="complete_behavior_blinded_reference_audit",
            passed=corpus_ok,
            detail="all SOURCE/TRUST/SINK/GUARD/ORDER/EFFECT and policy-equivalence labels pass",
        )
    )
    stage1 = _optional_json(root / config.stage1_report_path)
    stage1_ok = bool(stage1 and stage1.get("recommendation") == "continue_to_stage2")
    checks.append(
        PreflightCheck(
            check="stage1_continue_to_stage2",
            passed=stage1_ok,
            detail=str((stage1 or {}).get("recommendation", "missing Stage 1 report")),
        )
    )
    gpu_name, cuda_version = _gpu_identity()
    gpu_ok = config.expected_gpu_pattern.lower() in gpu_name.lower()
    checks.append(
        PreflightCheck(
            check="expected_cuda_gpu",
            passed=gpu_ok,
            detail=f"gpu={gpu_name}; cuda={cuda_version}",
        )
    )
    packages = _package_versions()
    required = ("torch", "transformers", "trl", "peft", "datasets", "accelerate", "bitsandbytes")
    package_ok = all(name in packages for name in required)
    checks.append(
        PreflightCheck(
            check="stage2_packages_installed",
            passed=package_ok,
            detail=json.dumps(packages, sort_keys=True),
        )
    )
    report = Stage2PreflightReport(
        created_at=_now(),
        config_sha256=_sha(config_path.read_bytes()),
        host={"platform": platform.platform(), "python": platform.python_version()},
        checks=tuple(checks),
        ready_for_dataset_freeze=split_ok and corpus_ok,
        ready_for_training=all(check.passed for check in checks),
    )
    _write_model(output_path, report)
    return report


def freeze_stage2_dataset(
    config_path: Path, repository_root: Path, destination: Path
) -> Stage2DatasetManifest:
    """Validate split inheritance and human reference audits, then freeze JSONL by split."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    split_path = root / config.split_manifest_path
    corpus_path = root / config.reference_corpus_path
    audit_path = root / config.reference_audit_path
    split = _load(Stage2SplitManifest, split_path)
    corpus = _load(Stage2ReferenceCorpus, corpus_path)
    audit = _load(Stage2ReferenceAudit, audit_path)
    if split.status != "frozen":
        raise Stage2Error("Stage 2 data cannot freeze from a draft split")
    if audit.corpus_sha256 != _sha(corpus_path.read_bytes()):
        raise Stage2Error("reference audit is bound to another corpus")
    if audit.split_manifest_sha256 != _sha(split_path.read_bytes()):
        raise Stage2Error("reference audit is bound to another split")
    assignments = {row.base_task_id: row for row in split.assignments}
    if {row.base_task_id for row in corpus.rows} != set(assignments):
        raise Stage2Error("reference corpus must cover every and only frozen base tasks")
    audit_by_id = {row.row_id: row for row in audit.rows}
    if set(audit_by_id) != {row.row_id for row in corpus.rows}:
        raise Stage2Error("reference audit row IDs do not exactly cover the corpus")
    row_hashes = {row.row_id: _model_sha(row) for row in corpus.rows}
    for row in corpus.rows:
        assignment = assignments[row.base_task_id]
        if row.split is not assignment.split:
            raise Stage2Error(f"derived-row split leakage: {row.row_id}")
        audited = audit_by_id[row.row_id]
        if audited.row_sha256 != row_hashes[row.row_id] or not audited.passed:
            raise Stage2Error(f"reference row lacks a passed exact-hash audit: {row.row_id}")
    _validate_reference_matrix(corpus.rows)
    if destination.exists():
        raise Stage2Error(f"refusing to overwrite dataset directory: {destination}")
    destination.mkdir(parents=True)
    files: dict[SplitName, FrozenDatasetFile] = {}
    base_by_split: dict[SplitName, tuple[str, ...]] = {}
    for split_name in SplitName:
        selected = sorted(
            (row for row in corpus.rows if row.split is split_name), key=lambda row: row.row_id
        )
        frozen = [
            FrozenDatasetRow(
                row_id=row.row_id,
                base_task_id=row.base_task_id,
                split=row.split,
                policy=row.policy,
                plan_format=row.plan_format,
                prompt=row.prompt,
                completion=row.completion,
                source_row_sha256=row_hashes[row.row_id],
            )
            for row in selected
        ]
        relative = f"{split_name.value}.jsonl"
        payload = "".join(item.model_dump_json() + "\n" for item in frozen)
        _write_new(destination / relative, payload)
        files[split_name] = FrozenDatasetFile(
            path=relative, sha256=_sha((destination / relative).read_bytes()), rows=len(frozen)
        )
        base_by_split[split_name] = tuple(
            sorted({item.base_task_id for item in frozen})
        )
    task_hashes = {
        item.base_task_id: _sha((root / item.task_path).read_bytes())
        for item in split.assignments
    }
    manifest = Stage2DatasetManifest(
        created_at=_now(),
        split_manifest_sha256=_sha(split_path.read_bytes()),
        corpus_sha256=_sha(corpus_path.read_bytes()),
        audit_sha256=_sha(audit_path.read_bytes()),
        task_sha256s=task_hashes,
        files=files,
        base_tasks_by_split=base_by_split,
    )
    _write_model(destination / "manifest.json", manifest)
    return manifest


def prepare_stage2_training_manifest(
    config_path: Path,
    repository_root: Path,
    dataset_manifest_path: Path,
    run_directory: Path,
    run_id: str,
) -> Stage2TrainingManifest:
    """Freeze an authorized PC training run only after all data, Stage 1, GPU, and package gates."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    preflight_path = run_directory.parent / f"{run_id}-preflight.json"
    preflight = audit_stage2_preflight(config_path, root, preflight_path)
    if not preflight.ready_for_training:
        failed = [check.check for check in preflight.checks if not check.passed]
        raise Stage2Error(f"Stage 2 training preflight failed: {failed}")
    dataset = _load(Stage2DatasetManifest, dataset_manifest_path)
    _validate_dataset_files(dataset, dataset_manifest_path.parent)
    stage1_path = root / config.stage1_report_path
    stage1 = _optional_json(stage1_path)
    if not stage1 or stage1.get("recommendation") != "continue_to_stage2":
        raise Stage2Error("Stage 1 has not authorized Stage 2")
    if run_directory.exists():
        raise Stage2Error(f"refusing to overwrite training run: {run_directory}")
    run_directory.mkdir(parents=True)
    gpu_name, cuda_version = _gpu_identity()
    manifest = Stage2TrainingManifest(
        run_id=run_id,
        created_at=_now(),
        config_path=os.path.relpath(config_path.resolve(), root),
        config_sha256=_sha(config_path.read_bytes()),
        dataset_manifest_path=os.path.relpath(dataset_manifest_path.resolve(), root),
        dataset_manifest_sha256=_sha(dataset_manifest_path.read_bytes()),
        stage1_report_sha256=_sha(stage1_path.read_bytes()),
        model=config.model,
        qlora=config.qlora,
        package_versions=_package_versions(),
        gpu_name=gpu_name,
        cuda_version=cuda_version,
        output_directory=os.path.relpath(run_directory.resolve() / "checkpoints", root),
    )
    _write_model(run_directory / "manifest.json", manifest)
    return manifest


def _validate_reference_matrix(rows: tuple[ReferencePlanRow, ...]) -> None:
    grouped: dict[
        tuple[str, SplitName, str, str, str], set[tuple[PolicyValue, Stage1PlanFormat]]
    ] = {}
    for row in rows:
        grouped.setdefault(row.variant_key, set()).add((row.policy, row.plan_format))
    expected = {(policy, plan_format) for policy in PolicyValue for plan_format in Stage1PlanFormat}
    incomplete = [key for key, cells in grouped.items() if cells != expected]
    if incomplete:
        raise Stage2Error(
            "each paraphrase variant requires A/B structured/freeform rows: "
            f"{incomplete[:3]}"
        )


def _validate_dataset_files(manifest: Stage2DatasetManifest, directory: Path) -> None:
    split_ids: dict[SplitName, set[str]] = {}
    for split_name, artifact in manifest.files.items():
        path = directory / artifact.path
        if not path.is_file() or _sha(path.read_bytes()) != artifact.sha256:
            raise Stage2Error(f"frozen {split_name.value} dataset hash mismatch")
        rows = [
            FrozenDatasetRow.model_validate_json(line)
            for line in path.read_text().splitlines()
        ]
        if len(rows) != artifact.rows or any(row.split is not split_name for row in rows):
            raise Stage2Error(f"frozen {split_name.value} dataset contents mismatch")
        split_ids[split_name] = {row.base_task_id for row in rows}
    if (
        split_ids[SplitName.TRAIN] & split_ids[SplitName.DEV]
        or split_ids[SplitName.TRAIN] & split_ids[SplitName.TEST]
        or split_ids[SplitName.DEV] & split_ids[SplitName.TEST]
    ):
        raise Stage2Error("base-task leakage exists across frozen dataset files")


def _gpu_identity() -> tuple[str, str]:
    try:
        process = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable", "unavailable"
    if process.returncode != 0 or not process.stdout.strip():
        return "unavailable", "unavailable"
    first = process.stdout.splitlines()[0]
    name, _, driver = first.partition(",")
    try:
        import torch  # type: ignore[import-not-found]

        cuda = torch.version.cuda or "none"
    except ImportError:
        cuda = "torch-not-installed"
    return name.strip(), f"runtime={cuda}; driver={driver.strip()}"


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in (
        "torch",
        "transformers",
        "trl",
        "peft",
        "datasets",
        "accelerate",
        "bitsandbytes",
    ):
        with suppress(importlib.metadata.PackageNotFoundError):
            versions[name] = importlib.metadata.version(name)
    return versions


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise Stage2Error(f"could not load {path}: {error}") from error


def _optional_model(model: type[ModelT], path: Path) -> ModelT | None:
    try:
        return _load(model, path)
    except Stage2Error:
        return None


def _optional_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _model_sha(model: StrictModel) -> str:
    return _sha(model.model_dump_json().encode())


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_model(path: Path, model: StrictModel) -> None:
    _write_new(path, model.model_dump_json(indent=2) + "\n")


def _write_new(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
