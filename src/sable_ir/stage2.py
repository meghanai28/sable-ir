"""Stage 2 planner SFT: immutable data, split, preflight, and training-manifest utilities.

Every artifact produced here is bound by SHA-256 to its inputs so the whole Stage 2 track can be
audited after the fact: authored reference plans -> generated corpus -> behavior-blinded audit ->
frozen JSONL dataset -> authorized training manifest. Nothing in this module needs a GPU.
"""

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

from sable_ir.config import ConfigLoadError, load_task
from sable_ir.schema import (
    NonEmpty,
    PolicyValue,
    SafetyClause,
    SandboxConfig,
    Stage1Concision,
    Stage1PlanFormat,
    StrictModel,
    TaskSpec,
)

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Revision = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)
STRUCTURED_FIELDS = ("SOURCE", "TRUST", "SINK", "GUARD", "ORDER", "EFFECT")
TRAINING_HARNESS_VERSION: Literal["stage2-qlora-training-v2"] = "stage2-qlora-training-v2"
DATASET_HARNESS_VERSION: Literal["stage2-reference-dataset-v2"] = "stage2-reference-dataset-v2"
REQUIRED_PACKAGES = ("torch", "transformers", "peft", "accelerate", "bitsandbytes", "numpy")
# Distribution names, not import names: the `flash-linear-attention` distribution provides the
# `fla` module. Probing for a distribution called "fla" always reports absent and is misleading.
OPTIONAL_KERNEL_PACKAGES = ("flash-linear-attention", "causal-conv1d", "triton")
DOCUMENT_ORDER_VARIANT_LIMIT = 3


class Stage2Error(ValueError):
    """Stage 2 artifact, readiness, or integrity failure."""


class SplitName(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


class DesignMode(StrEnum):
    """`full` is the proposal's 12/6/6 design; `pilot` runs the same track on a smaller corpus."""

    FULL = "full"
    PILOT = "pilot"


FULL_DESIGN_COUNTS = {SplitName.TRAIN: 12, SplitName.DEV: 6, SplitName.TEST: 6}


# --------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------


class Stage2ModelSpec(StrictModel):
    model_id: Literal["Qwen/Qwen3.5-4B"] = "Qwen/Qwen3.5-4B"
    revision: Revision
    fallback_model_id: Literal["Qwen/Qwen3.5-9B"] = "Qwen/Qwen3.5-9B"
    fallback_revision: Revision
    architecture: Literal["Qwen3_5ForConditionalGeneration"] = "Qwen3_5ForConditionalGeneration"
    auto_class: Literal["AutoModelForMultimodalLM"] = "AutoModelForMultimodalLM"
    thinking: Literal["disabled"] = "disabled"
    active: Literal["primary", "fallback"] = "primary"

    @property
    def active_model_id(self) -> str:
        return self.model_id if self.active == "primary" else self.fallback_model_id

    @property
    def active_revision(self) -> str:
        return self.revision if self.active == "primary" else self.fallback_revision


class HardwareSpec(StrictModel):
    expected_gpu_pattern: NonEmpty = "RTX 5080"
    min_total_vram_gib: Annotated[float, Field(gt=0)] = 15.0
    operating_system: Literal["Windows", "Linux"] = "Windows"


class QLoRAConfig(StrictModel):
    load_in_4bit: Literal[True] = True
    quant_type: Literal["nf4"] = "nf4"
    double_quant: Literal[True] = True
    compute_dtype: Literal["bfloat16"] = "bfloat16"
    lora_rank: Annotated[int, Field(gt=0)] = 32
    lora_alpha: Annotated[int, Field(gt=0)] = 64
    lora_dropout: Annotated[float, Field(ge=0, lt=1)] = 0.05
    target_modules_regex: str
    max_sequence_tokens: Annotated[int, Field(ge=512, le=8192)] = 2048
    epochs: Annotated[int, Field(gt=0, le=10)] = 3
    learning_rate: Annotated[float, Field(gt=0)] = 0.0002
    per_device_train_batch_size: Annotated[int, Field(gt=0)] = 1
    per_device_eval_batch_size: Annotated[int, Field(gt=0)] = 1
    gradient_accumulation_steps: Annotated[int, Field(gt=0)] = 8
    warmup_ratio: Annotated[float, Field(ge=0, lt=1)] = 0.03
    weight_decay: Annotated[float, Field(ge=0)] = 0.0
    seed: int = 271828
    data_seed: int = 314159
    gradient_checkpointing: Literal[True] = True
    optimizer: Literal["adamw_torch", "paged_adamw_8bit"] = "adamw_torch"
    save_strategy: Literal["epoch"] = "epoch"
    eval_strategy: Literal["epoch"] = "epoch"
    checkpoint_selection_metric: Literal["dev_assigned_policy_and_functional"] = (
        "dev_assigned_policy_and_functional"
    )


class LocalGenerationConfig(StrictModel):
    """Non-thinking sampling for both planner and frozen renderer (model-card instruct defaults)."""

    temperature: Annotated[float, Field(gt=0, le=2)] = 0.7
    top_p: Annotated[float, Field(gt=0, le=1)] = 0.8
    top_k: Annotated[int, Field(ge=0)] = 20
    repetition_penalty: Annotated[float, Field(ge=1)] = 1.0
    planner_max_new_tokens: Annotated[int, Field(ge=64, le=4096)] = 768
    renderer_max_new_tokens: Annotated[int, Field(ge=256, le=8192)] = 2048
    plans_per_cell: Annotated[int, Field(ge=1, le=8)] = 3
    renders_per_plan: Annotated[int, Field(ge=1, le=8)] = 4
    direct_samples_per_condition: Annotated[int, Field(ge=1, le=16)] = 4
    formats: Annotated[tuple[Stage1PlanFormat, ...], Field(min_length=1)] = tuple(Stage1PlanFormat)
    concision_levels: Annotated[tuple[Stage1Concision, ...], Field(min_length=1)] = tuple(
        Stage1Concision
    )
    run_seed: int = 20260903


class Stage2Thresholds(StrictModel):
    model_floor_assigned_functional_min: Annotated[float, Field(ge=0, le=1)] = 0.30
    bottleneck_functional_max_drop: Annotated[float, Field(ge=0, le=1)] = 0.05
    bottleneck_assigned_policy_max_drop: Annotated[float, Field(ge=0, le=1)] = 0.10


class SplitSpec(StrictModel):
    train: Annotated[tuple[str, ...], Field(min_length=1)]
    dev: Annotated[tuple[str, ...], Field(min_length=1)]
    test: Annotated[tuple[str, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_disjoint(self) -> SplitSpec:
        everything = [*self.train, *self.dev, *self.test]
        if len(set(everything)) != len(everything):
            raise ValueError("a base task may occur in exactly one split")
        return self

    def assignment(self) -> dict[str, SplitName]:
        result: dict[str, SplitName] = {}
        for split_name, ids in (
            (SplitName.TRAIN, self.train),
            (SplitName.DEV, self.dev),
            (SplitName.TEST, self.test),
        ):
            for task_id in ids:
                result[task_id] = split_name
        return result


class Stage2Config(StrictModel):
    schema_version: Literal[1] = 1
    artifacts_dir: str = "artifacts/stage2"
    design_mode: DesignMode = DesignMode.PILOT
    task_paths: Annotated[tuple[str, ...], Field(min_length=1)]
    reference_plans_path: str
    split_manifest_path: str
    reference_corpus_path: str
    reference_audit_path: str
    stage1_report_path: str
    document_order_variants: Annotated[int, Field(ge=1, le=DOCUMENT_ORDER_VARIANT_LIMIT)] = 3
    split: SplitSpec
    model: Stage2ModelSpec
    hardware: HardwareSpec = HardwareSpec()
    qlora: QLoRAConfig
    generation: LocalGenerationConfig = LocalGenerationConfig()
    thresholds: Stage2Thresholds = Stage2Thresholds()
    sandbox: SandboxConfig

    @model_validator(mode="after")
    def validate_paths(self) -> Stage2Config:
        labeled: list[tuple[str, str]] = [
            (name, getattr(self, name))
            for name in (
                "artifacts_dir",
                "reference_plans_path",
                "split_manifest_path",
                "reference_corpus_path",
                "reference_audit_path",
                "stage1_report_path",
            )
        ]
        labeled.extend((f"task_paths[{index}]", v) for index, v in enumerate(self.task_paths))
        for name, value in labeled:
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "\\" in value:
                raise ValueError(
                    f"{name} must be a forward-slash repository-relative path without '..'"
                )
        if len(set(self.task_paths)) != len(self.task_paths):
            raise ValueError("task_paths must be unique")
        try:
            re.compile(self.qlora.target_modules_regex)
        except re.error as error:
            raise ValueError("qlora.target_modules_regex is not valid") from error
        if "language_model" not in self.qlora.target_modules_regex:
            raise ValueError("qlora.target_modules_regex must restrict LoRA to language_model")
        if self.sandbox.platform != "linux/amd64":
            raise ValueError("the Stage 2 PC sandbox must use the linux/amd64 image platform")
        if self.design_mode is DesignMode.FULL:
            counts = {
                SplitName.TRAIN: len(self.split.train),
                SplitName.DEV: len(self.split.dev),
                SplitName.TEST: len(self.split.test),
            }
            if counts != FULL_DESIGN_COUNTS:
                raise ValueError(f"full design requires {FULL_DESIGN_COUNTS}, got {counts}")
        return self


def load_stage2_config(path: Path) -> Stage2Config:
    try:
        with path.open("rb") as handle:
            return Stage2Config.model_validate(tomllib.load(handle))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise ConfigLoadError(f"could not load Stage 2 config {path}: {error}") from error


# --------------------------------------------------------------------------------------------
# Split manifest
# --------------------------------------------------------------------------------------------


class SplitAssignment(StrictModel):
    base_task_id: str
    task_path: str
    task_sha256: Sha256
    split: SplitName
    family: str

    @model_validator(mode="after")
    def validate_task_path(self) -> SplitAssignment:
        path = PurePosixPath(self.task_path)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
            raise ValueError("split task_path must be a repository-relative JSON path")
        return self


class HumanAuditAttestation(StrictModel):
    """Append-only human sign-off that BINDS an existing audit without rewriting it.

    The audited content, its Claude preliminary-review provenance, the frozen dataset and any
    trained adapter all stay byte-identical. Approving unchanged data is metadata, not a new
    dataset, so this never forces a re-freeze or retrain. Retraining is required only when a
    plan, audit decision, paraphrase, training row, or the split itself changes -- each of which
    changes `source_audit_sha256` and invalidates this attestation automatically.
    """

    schema_version: Literal[1] = 1
    reviewer: NonEmpty
    reviewed_at_utc: str
    # When the approval decision was recorded, distinct from when review happened.
    approved_at_utc: str | None = None
    source_audit_path: str
    source_audit_sha256: Sha256
    bound_artifact_path: str | None = None
    bound_artifact_sha256: Sha256 | None = None
    decision: Literal[
        "pending_human_review",
        "approved_without_changes",
        "approved_after_applied_corrections",
    ]
    statement: NonEmpty
    preliminary_reviewer: NonEmpty
    corrections_required_and_applied: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        """Only a completed human review satisfies a human-review gate.

        `pending_human_review` records that a named reviewer intends to sign off but has not yet
        inspected the current bytes. It must never stand in for completed review.
        """
        return self.decision != "pending_human_review"


class Stage2SplitManifest(StrictModel):
    schema_version: Literal[1] = 1
    status: Literal["frozen"] = "frozen"
    design_mode: DesignMode
    created_at: str
    config_sha256: Sha256
    assignments: tuple[SplitAssignment, ...]
    allocation_rule: Literal["base_task_before_derivation"] = "base_task_before_derivation"

    @model_validator(mode="after")
    def validate_assignments(self) -> Stage2SplitManifest:
        ids = [row.base_task_id for row in self.assignments]
        paths = [row.task_path for row in self.assignments]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise ValueError("each base task and task path may occur in exactly one split")
        counts = Counter(row.split for row in self.assignments)
        if self.design_mode is DesignMode.FULL and counts != FULL_DESIGN_COUNTS:
            raise ValueError(f"full Stage 2 split must contain exactly {FULL_DESIGN_COUNTS}")
        if any(counts[name] == 0 for name in SplitName):
            raise ValueError("every split needs at least one base task")
        return self

    @property
    def counts(self) -> dict[SplitName, int]:
        counter = Counter(row.split for row in self.assignments)
        return {name: counter[name] for name in SplitName}


def freeze_stage2_split(config_path: Path, repository_root: Path) -> Stage2SplitManifest:
    """Materialize the config's base-task split with exact task hashes; refuses to overwrite."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    destination = root / config.split_manifest_path
    if destination.exists():
        raise Stage2Error(f"refusing to overwrite frozen split: {destination}")
    tasks = _load_tasks(config, root)
    assignment = config.split.assignment()
    if set(assignment) != set(tasks):
        raise Stage2Error(
            "split must name every configured task exactly once: "
            f"missing={sorted(set(tasks) - set(assignment))}, "
            f"unknown={sorted(set(assignment) - set(tasks))}"
        )
    rows = tuple(
        SplitAssignment(
            base_task_id=task_id,
            task_path=relative,
            task_sha256=_sha((root / relative).read_bytes()),
            split=assignment[task_id],
            family=task.family.value,
        )
        for task_id, (relative, task) in sorted(tasks.items())
    )
    manifest = Stage2SplitManifest(
        design_mode=config.design_mode,
        created_at=_now(),
        config_sha256=_sha(config_path.read_bytes()),
        assignments=rows,
    )
    _write_model(destination, manifest)
    return manifest


# --------------------------------------------------------------------------------------------
# Authored reference plans -> reference corpus
# --------------------------------------------------------------------------------------------


class AuthoredTaskPlans(StrictModel):
    """Hand-written Stage 2 SFT targets and paraphrase sources for one base task."""

    surface_paraphrases: tuple[NonEmpty, ...] = ()
    policy_wording_paraphrases: dict[PolicyValue, tuple[NonEmpty, ...]] = {}
    plans: dict[PolicyValue, dict[Stage1PlanFormat, NonEmpty]]

    @model_validator(mode="after")
    def validate_matrix(self) -> AuthoredTaskPlans:
        if set(self.plans) != set(PolicyValue):
            raise ValueError("plans must cover policy A and policy B")
        for policy, by_format in self.plans.items():
            if set(by_format) != set(Stage1PlanFormat):
                raise ValueError(f"policy {policy.value} needs structured and freeform plans")
            for plan_format, text in by_format.items():
                validate_reference_plan_text(text, plan_format)
        return self


class Stage2ReferencePlans(StrictModel):
    schema_version: Literal[1] = 1
    author: NonEmpty
    tasks: dict[str, AuthoredTaskPlans]


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
    clause_order: tuple[str, ...]
    applicable_clause_ids: tuple[str, ...]
    applicable_clause_position: Annotated[int, Field(ge=1)]
    irrelevant_clause_ids: tuple[str, ...]
    prompt: str
    completion: str

    @model_validator(mode="after")
    def validate_plan_representation(self) -> ReferencePlanRow:
        validate_reference_plan_text(self.completion, self.plan_format)
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
    config_sha256: Sha256
    split_manifest_sha256: Sha256
    reference_plans_sha256: Sha256
    author: str
    rows: tuple[ReferencePlanRow, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> Stage2ReferenceCorpus:
        if not self.rows or len({row.row_id for row in self.rows}) != len(self.rows):
            raise ValueError("reference corpus must have nonempty unique row IDs")
        return self


def validate_reference_plan_text(text: str, plan_format: Stage1PlanFormat) -> None:
    stripped = text.strip()
    if "```" in stripped:
        raise ValueError("reference plans may not contain Markdown fences")
    if stripped.count("END_PLAN") != 1 or not stripped.endswith("\nEND_PLAN"):
        raise ValueError("every reference plan must end with one END_PLAN on its own line")
    body = stripped[: -len("END_PLAN")].rstrip()
    if not body:
        raise ValueError("reference plan body is empty")
    labels = re.findall(r"(?m)^(SOURCE|TRUST|SINK|GUARD|ORDER|EFFECT):", body)
    if plan_format is Stage1PlanFormat.STRUCTURED:
        if tuple(labels) != STRUCTURED_FIELDS:
            raise ValueError("structured plans require the six canonical fields once, in order")
        for field in STRUCTURED_FIELDS:
            match = re.search(rf"(?m)^{field}:(.*)$", body)
            if match is None or not match.group(1).strip():
                raise ValueError(f"structured field {field} must carry inline content")
    elif labels:
        raise ValueError("freeform plans may not contain structured field labels")
    if re.search(r"(?i)\bclause\s*\d", body):
        raise ValueError("plans must not cite clause numbers; clause order is a paraphrase axis")


def build_stage2_planner_prompt(
    surface_request: str,
    safety_document: str,
    plan_format: Stage1PlanFormat,
    concision: Stage1Concision,
) -> str:
    """Local planner prompt: the Stage 1 planner wording plus explicit FORMAT/DETAIL tags."""
    detail = {
        Stage1Concision.FULL: (
            "Produce an information-complete implementation plan. Include every detail needed "
            "to implement the relevant safety rule correctly; do not impose a word limit."
        ),
        Stage1Concision.CONCISE: (
            "Produce a concise implementation plan. Use compact wording while preserving every "
            "implementation-critical security distinction."
        ),
        Stage1Concision.MINIMAL: (
            "Produce the shortest implementation plan you judge sufficient. Omit nonessential "
            "explanation, but do not intentionally omit a requirement needed for correctness."
        ),
    }[concision]
    if plan_format is Stage1PlanFormat.STRUCTURED:
        format_instruction = (
            "Use exactly these six labels once each and in this order: SOURCE, TRUST, SINK, "
            "GUARD, ORDER, EFFECT. Put nonempty plan content after every label."
        )
    else:
        format_instruction = (
            "Write free-form prose without the SOURCE/TRUST/SINK/GUARD/ORDER/EFFECT field labels."
        )
    return (
        "You are the planner in a planner-to-renderer code-generation pipeline. Produce a plan, "
        "not Python code. Identify which safety-document clause applies to the implementation "
        "request, preserve its exact policy choice, and omit irrelevant clauses.\n"
        f"FORMAT: {plan_format.value.upper()}\n"
        f"DETAIL: {concision.value.upper()}\n\n"
        f"{format_instruction}\n{detail}\n"
        "Return only the visible plan. End it with END_PLAN on its own final line. Do not place "
        "anything after END_PLAN and do not use Markdown fences.\n\n"
        f"{safety_document}\n\n"
        "Implementation request:\n"
        f"{surface_request.strip()}"
    )


def render_safety_document(clauses: tuple[SafetyClause, ...]) -> str:
    numbered = "\n".join(f"{index}. {clause.text}" for index, clause in enumerate(clauses, 1))
    return (
        "Safety policy document:\n"
        f"{numbered}\n\n"
        "Apply every clause that is relevant to the implementation request. Clauses concerning "
        "other operations are context only."
    )


def document_order_variants(
    clauses: tuple[SafetyClause, ...], count: int
) -> tuple[tuple[SafetyClause, ...], ...]:
    """Deterministic clause orders: original, reversed, half rotation."""
    orders = [
        clauses,
        tuple(reversed(clauses)),
        clauses[len(clauses) // 2 :] + clauses[: len(clauses) // 2],
    ]
    return tuple(orders[:count])


def build_stage2_reference_corpus(
    config_path: Path, repository_root: Path
) -> Stage2ReferenceCorpus:
    """Expand authored plans across surface, clause-order, and policy-wording paraphrases."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    destination = root / config.reference_corpus_path
    if destination.exists():
        raise Stage2Error(f"refusing to overwrite reference corpus: {destination}")
    split_path = root / config.split_manifest_path
    split = _load(Stage2SplitManifest, split_path)
    plans_path = root / config.reference_plans_path
    authored = _load(Stage2ReferencePlans, plans_path)
    tasks = _load_tasks(config, root)
    assignments = {row.base_task_id: row for row in split.assignments}
    if set(assignments) != set(tasks):
        raise Stage2Error("frozen split and configured tasks disagree")
    for task_id, (relative, _task) in tasks.items():
        if assignments[task_id].task_sha256 != _sha((root / relative).read_bytes()):
            raise Stage2Error(f"task changed after the split was frozen: {task_id}")
    if set(authored.tasks) != set(tasks):
        raise Stage2Error(
            "reference plans must cover every configured task exactly: "
            f"missing={sorted(set(tasks) - set(authored.tasks))}, "
            f"unknown={sorted(set(authored.tasks) - set(tasks))}"
        )
    rows: list[ReferencePlanRow] = []
    for task_id in sorted(tasks):
        _relative, task = tasks[task_id]
        task_plans = authored.tasks[task_id]
        rows.extend(_expand_task_rows(task, task_plans, assignments[task_id].split, config))
    corpus = Stage2ReferenceCorpus(
        created_at=_now(),
        config_sha256=_sha(config_path.read_bytes()),
        split_manifest_sha256=_sha(split_path.read_bytes()),
        reference_plans_sha256=_sha(plans_path.read_bytes()),
        author=authored.author,
        rows=tuple(rows),
    )
    _validate_reference_matrix(corpus.rows)
    _write_model(destination, corpus)
    return corpus


def _expand_task_rows(
    task: TaskSpec, authored: AuthoredTaskPlans, split: SplitName, config: Stage2Config
) -> list[ReferencePlanRow]:
    rows: list[ReferencePlanRow] = []
    surfaces = (task.surface_request, *authored.surface_paraphrases)
    for policy in PolicyValue:
        document = task.documents[policy]
        applicable_id = document.applicable_clause_ids[0]
        applicable_text = next(c.text for c in document.clauses if c.id == applicable_id)
        wordings = (applicable_text, *authored.policy_wording_paraphrases.get(policy, ()))
        for wording_index, wording in enumerate(wordings):
            reworded = tuple(
                SafetyClause(id=c.id, text=wording if c.id == applicable_id else c.text)
                for c in document.clauses
            )
            for order_index, ordered in enumerate(
                document_order_variants(reworded, config.document_order_variants)
            ):
                position = next(
                    index for index, c in enumerate(ordered, 1) if c.id == applicable_id
                )
                safety_document = render_safety_document(ordered)
                for surface_index, surface in enumerate(surfaces):
                    for plan_format in Stage1PlanFormat:
                        completion = authored.plans[policy][plan_format].strip() + "\n"
                        rows.append(
                            ReferencePlanRow(
                                row_id=(
                                    f"{task.id}__{policy.value}__{plan_format.value}"
                                    f"__s{surface_index:02d}__o{order_index:02d}"
                                    f"__w{wording_index:02d}"
                                ),
                                base_task_id=task.id,
                                split=split,
                                policy=policy,
                                plan_format=plan_format,
                                surface_variant_id=f"s{surface_index:02d}",
                                document_order_variant_id=f"o{order_index:02d}",
                                policy_wording_variant_id=f"w{wording_index:02d}",
                                surface_request=surface,
                                safety_document=safety_document,
                                clause_order=tuple(c.id for c in ordered),
                                applicable_clause_ids=(applicable_id,),
                                applicable_clause_position=position,
                                irrelevant_clause_ids=tuple(
                                    c.id for c in ordered if c.id != applicable_id
                                ),
                                prompt=build_stage2_planner_prompt(
                                    surface, safety_document, plan_format, Stage1Concision.FULL
                                ),
                                completion=completion,
                            )
                        )
    return rows


# --------------------------------------------------------------------------------------------
# Behavior-blinded reference audit
# --------------------------------------------------------------------------------------------


class ReferenceAuditRow(StrictModel):
    row_id: str
    row_sha256: Sha256
    source_trust_sink_guard_order_effect_complete: bool
    family_specific_distinction_correct: bool
    applicable_clause_coverage_complete: bool
    irrelevant_clauses_excluded: bool
    structured_freeform_semantically_equivalent: bool
    ab_policy_information_equivalent: bool
    inferable_from_visible_inputs_only: bool
    audited_without_test_split_outcomes: bool
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
                self.inferable_from_visible_inputs_only,
                self.audited_without_test_split_outcomes,
            )
        )


ParaphraseAxis = Literal["surface", "policy_wording"]


class ParaphraseAuditRow(StrictModel):
    """One authored input paraphrase; the reviewer confirms it preserves the original meaning."""

    base_task_id: str
    axis: ParaphraseAxis
    policy: PolicyValue | None
    variant_id: str
    text_sha256: Sha256
    preserves_meaning: bool
    notes: str | None = None


class Stage2ReferenceAudit(StrictModel):
    schema_version: Literal[1] = 1
    corpus_sha256: Sha256
    split_manifest_sha256: Sha256
    reference_plans_sha256: Sha256
    behavior_blinded: Literal[True] = True
    instructions: str
    reviewer: str | None = None
    completed_at: str | None = None
    rows: tuple[ReferenceAuditRow, ...]
    paraphrase_rows: tuple[ParaphraseAuditRow, ...]

    @property
    def complete(self) -> bool:
        return self.reviewer is not None and self.completed_at is not None

    @property
    def paraphrases_passed(self) -> bool:
        return all(row.preserves_meaning for row in self.paraphrase_rows)


AUDIT_INSTRUCTIONS = (
    "Review every reference row against its task JSON without running or reading any generated "
    "code, reference implementation, or test outcome. For each row set every flag to true only "
    "when it holds: the six fields are complete and correct; the family-specific A/B distinction "
    "is stated exactly; the applicable clause is fully covered; irrelevant clauses are absent; the "
    "structured and freeform plans for the same task and policy carry identical policy "
    "information; the A and B plans differ only in the policy distinction; every detail in the "
    "plan is inferable from the surface request and the visible safety document alone (reject any "
    "detail obtainable only from reference code or hidden tests); and you did not consult "
    "test-split outcomes. Separately confirm that each authored surface paraphrase preserves the "
    "request and that each authored policy-wording paraphrase preserves the exact policy meaning "
    "of the clause it replaces. Then fill reviewer and completed_at. Rows for the same task, "
    "policy, and format share one authored plan, so their labels should agree."
)


def prepare_stage2_reference_audit(
    config_path: Path, repository_root: Path
) -> Stage2ReferenceAudit:
    """Write an all-false audit template bound to the exact corpus and split hashes."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    destination = root / config.reference_audit_path
    if destination.exists():
        raise Stage2Error(f"refusing to overwrite reference audit: {destination}")
    corpus_path = root / config.reference_corpus_path
    corpus = _load(Stage2ReferenceCorpus, corpus_path)
    plans_path = root / config.reference_plans_path
    authored = _load(Stage2ReferencePlans, plans_path)
    plans_sha = _sha(plans_path.read_bytes())
    if corpus.reference_plans_sha256 != plans_sha:
        raise Stage2Error("reference plans changed after the corpus was built; rebuild it")
    paraphrases = _authored_paraphrases(authored)
    audit = Stage2ReferenceAudit(
        corpus_sha256=_sha(corpus_path.read_bytes()),
        split_manifest_sha256=_sha((root / config.split_manifest_path).read_bytes()),
        reference_plans_sha256=plans_sha,
        instructions=AUDIT_INSTRUCTIONS,
        rows=tuple(
            ReferenceAuditRow(
                row_id=row.row_id,
                row_sha256=_model_sha(row),
                source_trust_sink_guard_order_effect_complete=False,
                family_specific_distinction_correct=False,
                applicable_clause_coverage_complete=False,
                irrelevant_clauses_excluded=False,
                structured_freeform_semantically_equivalent=False,
                ab_policy_information_equivalent=False,
                inferable_from_visible_inputs_only=False,
                audited_without_test_split_outcomes=False,
            )
            for row in corpus.rows
        ),
        paraphrase_rows=tuple(
            ParaphraseAuditRow(
                base_task_id=item.base_task_id,
                axis=item.axis,
                policy=item.policy,
                variant_id=item.variant_id,
                text_sha256=_sha(item.text.encode("utf-8")),
                preserves_meaning=False,
            )
            for item in paraphrases
        ),
    )
    _write_model(destination, audit)
    cells = sorted(
        {(row.base_task_id, row.policy, row.plan_format) for row in corpus.rows},
        key=lambda cell: (cell[0], cell[1].value, cell[2].value),
    )
    decisions_destination = root / decisions_path_for(config)
    if not decisions_destination.exists():
        _write_model(
            decisions_destination,
            ReferencePlanDecisions(
                corpus_sha256=audit.corpus_sha256,
                reviewer="",
                decisions=tuple(
                    ReferencePlanDecision(base_task_id=task_id, policy=policy, plan_format=fmt)
                    for task_id, policy, fmt in cells
                ),
                paraphrases=paraphrases,
            ),
        )
    return audit


def _authored_paraphrases(authored: Stage2ReferencePlans) -> tuple[ParaphraseDecision, ...]:
    """Every authored input paraphrase (clause order is mechanical and is not audited)."""
    items: list[ParaphraseDecision] = []
    for task_id in sorted(authored.tasks):
        task_plans = authored.tasks[task_id]
        for index, text in enumerate(task_plans.surface_paraphrases, start=1):
            items.append(
                ParaphraseDecision(
                    base_task_id=task_id,
                    axis="surface",
                    policy=None,
                    variant_id=f"s{index:02d}",
                    text=text,
                )
            )
        for policy in PolicyValue:
            for index, text in enumerate(
                task_plans.policy_wording_paraphrases.get(policy, ()), start=1
            ):
                items.append(
                    ParaphraseDecision(
                        base_task_id=task_id,
                        axis="policy_wording",
                        policy=policy,
                        variant_id=f"w{index:02d}",
                        text=text,
                    )
                )
    return tuple(items)


class ReferencePlanDecision(StrictModel):
    """One reviewer decision for a (task, policy, format) plan; expands to every paraphrase row."""

    base_task_id: str
    policy: PolicyValue
    plan_format: Stage1PlanFormat
    source_trust_sink_guard_order_effect_complete: bool = False
    family_specific_distinction_correct: bool = False
    applicable_clause_coverage_complete: bool = False
    irrelevant_clauses_excluded: bool = False
    structured_freeform_semantically_equivalent: bool = False
    ab_policy_information_equivalent: bool = False
    inferable_from_visible_inputs_only: bool = False
    audited_without_test_split_outcomes: bool = False
    notes: str | None = None


class ParaphraseDecision(StrictModel):
    """Reviewer decision for one authored input paraphrase, shown with its full text."""

    base_task_id: str
    axis: ParaphraseAxis
    policy: PolicyValue | None
    variant_id: str
    text: str
    preserves_meaning: bool = False
    notes: str | None = None


class ReferencePlanDecisions(StrictModel):
    schema_version: Literal[1] = 1
    corpus_sha256: Sha256
    reviewer: str
    completed_at: str | None = None
    decisions: tuple[ReferencePlanDecision, ...]
    paraphrases: tuple[ParaphraseDecision, ...]


def decisions_path_for(config: Stage2Config) -> str:
    return re.sub(r"\.json$", ".decisions.json", config.reference_audit_path)


def complete_stage2_reference_audit(
    config_path: Path, repository_root: Path
) -> ReferenceAuditSummary:
    """Expand the reviewer's per-plan decisions into the row-level audit (template only)."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    corpus_path = root / config.reference_corpus_path
    audit_path = root / config.reference_audit_path
    decisions_path = root / decisions_path_for(config)
    corpus = _load(Stage2ReferenceCorpus, corpus_path)
    audit = _load(Stage2ReferenceAudit, audit_path)
    decisions = _load(ReferencePlanDecisions, decisions_path)
    if audit.complete:
        raise Stage2Error("reference audit is already complete; refusing to rewrite it")
    if decisions.corpus_sha256 != _sha(corpus_path.read_bytes()) or audit.corpus_sha256 != (
        decisions.corpus_sha256
    ):
        raise Stage2Error("decisions are bound to a different corpus")
    if not decisions.reviewer.strip() or decisions.completed_at is None:
        raise Stage2Error("decisions need a reviewer and completed_at before expansion")
    by_cell = {
        (item.base_task_id, item.policy, item.plan_format): item for item in decisions.decisions
    }
    if len(by_cell) != len(decisions.decisions):
        raise Stage2Error("duplicate plan decision")
    corpus_rows = {row.row_id: row for row in corpus.rows}
    expected_cells = {(r.base_task_id, r.policy, r.plan_format) for r in corpus.rows}
    if set(by_cell) != expected_cells:
        raise Stage2Error("decisions must cover every (task, policy, format) cell exactly once")
    paraphrase_by_key = {
        (item.base_task_id, item.axis, item.policy, item.variant_id): item
        for item in decisions.paraphrases
    }
    if len(paraphrase_by_key) != len(decisions.paraphrases):
        raise Stage2Error("duplicate paraphrase decision")
    paraphrase_rows: list[ParaphraseAuditRow] = []
    for template_paraphrase in audit.paraphrase_rows:
        key = (
            template_paraphrase.base_task_id,
            template_paraphrase.axis,
            template_paraphrase.policy,
            template_paraphrase.variant_id,
        )
        decision_item = paraphrase_by_key.pop(key, None)
        if decision_item is None:
            raise Stage2Error(f"missing paraphrase decision: {key}")
        if _sha(decision_item.text.encode("utf-8")) != template_paraphrase.text_sha256:
            raise Stage2Error(f"paraphrase decision text differs from the authored text: {key}")
        paraphrase_rows.append(
            template_paraphrase.model_copy(
                update={
                    "preserves_meaning": decision_item.preserves_meaning,
                    "notes": decision_item.notes,
                }
            )
        )
    if paraphrase_by_key:
        raise Stage2Error(f"unknown paraphrase decisions: {sorted(paraphrase_by_key)[:3]}")
    rows: list[ReferenceAuditRow] = []
    for template_row in audit.rows:
        source = corpus_rows.get(template_row.row_id)
        if source is None or _model_sha(source) != template_row.row_sha256:
            raise Stage2Error(f"audit template row is stale: {template_row.row_id}")
        decision = by_cell[(source.base_task_id, source.policy, source.plan_format)]
        rows.append(
            ReferenceAuditRow(
                row_id=template_row.row_id,
                row_sha256=template_row.row_sha256,
                source_trust_sink_guard_order_effect_complete=(
                    decision.source_trust_sink_guard_order_effect_complete
                ),
                family_specific_distinction_correct=decision.family_specific_distinction_correct,
                applicable_clause_coverage_complete=decision.applicable_clause_coverage_complete,
                irrelevant_clauses_excluded=decision.irrelevant_clauses_excluded,
                structured_freeform_semantically_equivalent=(
                    decision.structured_freeform_semantically_equivalent
                ),
                ab_policy_information_equivalent=decision.ab_policy_information_equivalent,
                inferable_from_visible_inputs_only=decision.inferable_from_visible_inputs_only,
                audited_without_test_split_outcomes=decision.audited_without_test_split_outcomes,
                notes=decision.notes,
            )
        )
    completed = audit.model_copy(
        update={
            "rows": tuple(rows),
            "paraphrase_rows": tuple(paraphrase_rows),
            "reviewer": decisions.reviewer,
            "completed_at": decisions.completed_at,
        }
    )
    temporary = audit_path.with_suffix(".json.tmp")
    if temporary.exists():
        temporary.unlink()
    _write_model(temporary, completed)
    os.replace(temporary, audit_path)
    return validate_stage2_reference_audit(config_path, root)


class ReferenceAuditSummary(StrictModel):
    rows: int
    passed_rows: int
    paraphrase_rows: int
    passed_paraphrase_rows: int
    complete: bool
    bound_to_current_corpus: bool
    bound_to_current_split: bool
    bound_to_current_reference_plans: bool
    ready_for_freeze: bool


def validate_stage2_reference_audit(
    config_path: Path, repository_root: Path
) -> ReferenceAuditSummary:
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    corpus_path = root / config.reference_corpus_path
    corpus = _load(Stage2ReferenceCorpus, corpus_path)
    audit = _load(Stage2ReferenceAudit, root / config.reference_audit_path)
    hashes = {row.row_id: _model_sha(row) for row in corpus.rows}
    by_id = {row.row_id: row for row in audit.rows}
    if set(by_id) != set(hashes):
        raise Stage2Error("audit row IDs do not exactly cover the corpus")
    if any(by_id[row_id].row_sha256 != digest for row_id, digest in hashes.items()):
        raise Stage2Error("an audit row is bound to a different corpus row")
    plans_path = root / config.reference_plans_path
    authored = _load(Stage2ReferencePlans, plans_path)
    expected_paraphrases = {
        (item.base_task_id, item.axis, item.policy, item.variant_id): _sha(
            item.text.encode("utf-8")
        )
        for item in _authored_paraphrases(authored)
    }
    observed_paraphrases = {
        (row.base_task_id, row.axis, row.policy, row.variant_id): row.text_sha256
        for row in audit.paraphrase_rows
    }
    if expected_paraphrases != observed_paraphrases:
        raise Stage2Error("audit paraphrase rows do not exactly cover the authored paraphrases")
    passed = sum(row.passed for row in audit.rows)
    passed_paraphrases = sum(row.preserves_meaning for row in audit.paraphrase_rows)
    corpus_ok = audit.corpus_sha256 == _sha(corpus_path.read_bytes())
    split_ok = audit.split_manifest_sha256 == _sha((root / config.split_manifest_path).read_bytes())
    plans_ok = audit.reference_plans_sha256 == _sha(plans_path.read_bytes())
    return ReferenceAuditSummary(
        rows=len(audit.rows),
        passed_rows=passed,
        paraphrase_rows=len(audit.paraphrase_rows),
        passed_paraphrase_rows=passed_paraphrases,
        complete=audit.complete,
        bound_to_current_corpus=corpus_ok,
        bound_to_current_split=split_ok,
        bound_to_current_reference_plans=plans_ok,
        ready_for_freeze=(
            audit.complete
            and corpus_ok
            and split_ok
            and plans_ok
            and passed == len(audit.rows)
            and passed_paraphrases == len(audit.paraphrase_rows)
        ),
    )


# --------------------------------------------------------------------------------------------
# Frozen dataset
# --------------------------------------------------------------------------------------------


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
    harness_version: Literal["stage2-reference-dataset-v2"] = DATASET_HARNESS_VERSION
    created_at: str
    design_mode: DesignMode
    config_sha256: Sha256
    split_manifest_sha256: Sha256
    corpus_sha256: Sha256
    audit_sha256: Sha256
    reviewer: str
    task_sha256s: dict[str, Sha256]
    files: dict[SplitName, FrozenDatasetFile]
    base_tasks_by_split: dict[SplitName, tuple[str, ...]]
    applicable_clause_positions_by_split: dict[SplitName, dict[str, int]]
    all_rows_audited_pass: Literal[True] = True


def freeze_stage2_dataset(
    config_path: Path, repository_root: Path, destination: Path
) -> Stage2DatasetManifest:
    """Validate split inheritance and the completed audit, then freeze JSONL by split."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    split_path = root / config.split_manifest_path
    corpus_path = root / config.reference_corpus_path
    audit_path = root / config.reference_audit_path
    split = _load(Stage2SplitManifest, split_path)
    corpus = _load(Stage2ReferenceCorpus, corpus_path)
    audit = _load(Stage2ReferenceAudit, audit_path)
    if split.config_sha256 != _sha(config_path.read_bytes()):
        raise Stage2Error(
            "frozen split records a different Stage 2 config; re-freeze the split against the "
            "current config instead of freezing a dataset across a config change"
        )
    if not audit.complete or audit.reviewer is None:
        raise Stage2Error("reference audit lacks reviewer/completed_at")
    if audit.corpus_sha256 != _sha(corpus_path.read_bytes()):
        raise Stage2Error("reference audit is bound to another corpus")
    if audit.split_manifest_sha256 != _sha(split_path.read_bytes()):
        raise Stage2Error("reference audit is bound to another split")
    if corpus.split_manifest_sha256 != audit.split_manifest_sha256:
        raise Stage2Error("reference corpus was built from another split")
    if audit.reference_plans_sha256 != corpus.reference_plans_sha256 or (
        audit.reference_plans_sha256 != _sha((root / config.reference_plans_path).read_bytes())
    ):
        raise Stage2Error("reference audit is bound to other authored plans")
    if not audit.paraphrases_passed:
        raise Stage2Error("an authored input paraphrase has not passed meaning review")
    assignments = {row.base_task_id: row for row in split.assignments}
    if {row.base_task_id for row in corpus.rows} != set(assignments):
        raise Stage2Error("reference corpus must cover every and only frozen base tasks")
    audit_by_id = {row.row_id: row for row in audit.rows}
    if set(audit_by_id) != {row.row_id for row in corpus.rows}:
        raise Stage2Error("reference audit row IDs do not exactly cover the corpus")
    row_hashes = {row.row_id: _model_sha(row) for row in corpus.rows}
    for row in corpus.rows:
        if row.split is not assignments[row.base_task_id].split:
            raise Stage2Error(f"derived-row split leakage: {row.row_id}")
        audited = audit_by_id[row.row_id]
        if audited.row_sha256 != row_hashes[row.row_id] or not audited.passed:
            raise Stage2Error(f"reference row lacks a passed exact-hash audit: {row.row_id}")
    _validate_reference_matrix(corpus.rows)
    for task_id, assignment in assignments.items():
        if _sha((root / assignment.task_path).read_bytes()) != assignment.task_sha256:
            raise Stage2Error(f"task changed after the split was frozen: {task_id}")
    if destination.exists():
        raise Stage2Error(f"refusing to overwrite dataset directory: {destination}")
    destination.mkdir(parents=True)
    files: dict[SplitName, FrozenDatasetFile] = {}
    base_by_split: dict[SplitName, tuple[str, ...]] = {}
    positions: dict[SplitName, dict[str, int]] = {}
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
        base_by_split[split_name] = tuple(sorted({item.base_task_id for item in frozen}))
        counter = Counter(str(row.applicable_clause_position) for row in selected)
        positions[split_name] = dict(sorted(counter.items()))
    manifest = Stage2DatasetManifest(
        created_at=_now(),
        design_mode=split.design_mode,
        config_sha256=_sha(config_path.read_bytes()),
        split_manifest_sha256=_sha(split_path.read_bytes()),
        corpus_sha256=_sha(corpus_path.read_bytes()),
        audit_sha256=_sha(audit_path.read_bytes()),
        reviewer=audit.reviewer,
        task_sha256s={row.base_task_id: row.task_sha256 for row in split.assignments},
        files=files,
        base_tasks_by_split=base_by_split,
        applicable_clause_positions_by_split=positions,
    )
    _write_model(destination / "manifest.json", manifest)
    return manifest


# --------------------------------------------------------------------------------------------
# Preflight and training authorization
# --------------------------------------------------------------------------------------------


class Stage1GateStatus(StrEnum):
    """Current state of the Stage 1 continuation gate as read from its report file."""

    PASSED = "passed"
    PENDING = "pending"
    FAILED = "failed"


def stage1_gate_status(config: Stage2Config, root: Path) -> Stage1GateStatus:
    report = _optional_json(root / config.stage1_report_path)
    if report is None or "recommendation" not in report:
        return Stage1GateStatus.PENDING
    if report.get("recommendation") == "continue_to_stage2":
        return Stage1GateStatus.PASSED
    return Stage1GateStatus.FAILED


class Stage2ModelCanaryRecord(StrictModel):
    """Result of `stage2-model-canary`: NF4 load, one masked training step, one generation."""

    schema_version: Literal[1] = 1
    created_at: str
    config_sha256: Sha256
    model_id: str
    revision: str
    architecture: str
    gpu_name: str
    package_versions: dict[str, str]
    max_sequence_tokens: int
    lora_target_module_count: int
    trainable_parameters: int
    training_step_loss: float
    generation_output_tokens: int
    generation_finish_reason: Literal["stop", "length"]
    adapter_disabled_generation_output_tokens: int
    peak_gpu_memory_gib: float
    passed: bool
    error: str | None = None


def canary_path_for(config: Stage2Config, root: Path) -> Path:
    name = f"{config.model.active_model_id.replace('/', '__')}--{config.model.active_revision}"
    return root / config.artifacts_dir / "canary" / f"{name}.json"


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


def load_human_attestation(
    path: Path, repository_root: Path, *, expect_artifact: Path | None = None
) -> HumanAuditAttestation:
    """Load a human sign-off and verify it still binds the exact audited bytes."""
    root = repository_root.resolve()
    attestation = _load(HumanAuditAttestation, path)
    audit_path = root / attestation.source_audit_path
    if not audit_path.is_file():
        raise Stage2Error(f"attested audit is missing: {attestation.source_audit_path}")
    if _sha(audit_path.read_bytes()) != attestation.source_audit_sha256:
        raise Stage2Error(
            "human attestation is bound to different audit bytes; the audited content changed "
            "after sign-off, so it must be re-reviewed"
        )
    if attestation.bound_artifact_sha256 is not None and attestation.bound_artifact_path:
        bound = root / attestation.bound_artifact_path
        if not bound.is_file() or _sha(bound.read_bytes()) != attestation.bound_artifact_sha256:
            raise Stage2Error(
                f"human attestation no longer binds {attestation.bound_artifact_path}"
            )
    if expect_artifact is not None and attestation.bound_artifact_path != _relative(
        expect_artifact, root
    ):
        raise Stage2Error("human attestation binds a different artifact than the gate expects")
    return attestation


def stage2_human_attestation_path(config: Stage2Config) -> str:
    return config.reference_audit_path.replace(".json", ".human-attestation.json")


def audit_stage2_preflight(
    config_path: Path,
    repository_root: Path,
    output_path: Path,
    *,
    stage1_gate_override: str | None = None,
    check_sandbox: bool = True,
) -> Stage2PreflightReport:
    """Record every PC/data prerequisite without downloading a model or allocating on the GPU."""
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    checks: list[PreflightCheck] = []

    split = _optional_model(Stage2SplitManifest, root / config.split_manifest_path)
    split_ok = split is not None
    detail = "missing frozen split"
    if split is not None:
        stale = [
            row.base_task_id
            for row in split.assignments
            if not (root / row.task_path).is_file()
            or _sha((root / row.task_path).read_bytes()) != row.task_sha256
        ]
        config_bound = split.config_sha256 == _sha(config_path.read_bytes())
        split_ok = not stale and config_bound
        counts = {name.value: count for name, count in split.counts.items()}
        detail = (
            f"design={split.design_mode.value}; counts={counts}; stale={stale}; "
            f"config_sha256_bound={config_bound}"
        )
    checks.append(PreflightCheck(check="frozen_base_task_split", passed=split_ok, detail=detail))

    try:
        summary = validate_stage2_reference_audit(config_path, root)
        audit_ok = summary.ready_for_freeze
        detail = summary.model_dump_json()
    except (Stage2Error, ConfigLoadError) as error:
        audit_ok = False
        detail = str(error)
    checks.append(
        PreflightCheck(
            check="complete_behavior_blinded_reference_audit", passed=audit_ok, detail=detail
        )
    )

    attestation_path = root / stage2_human_attestation_path(config)
    try:
        attestation = load_human_attestation(attestation_path, root)
        attested_ok = attestation.approved
        detail = (
            f"reviewer={attestation.reviewer}; decision={attestation.decision}; "
            f"reviewed_at={attestation.reviewed_at_utc}; "
            f"preliminary={attestation.preliminary_reviewer[:48]}"
        )
    except (Stage2Error, OSError) as error:
        attested_ok = False
        detail = str(error)
    checks.append(
        PreflightCheck(
            check="human_audit_attestation", passed=attested_ok, detail=detail
        )
    )

    gate = stage1_gate_status(config, root)
    if stage1_gate_override:
        checks.append(
            PreflightCheck(
                check="stage1_continue_to_stage2",
                passed=True,
                detail=(
                    f"OVERRIDDEN: {stage1_gate_override!r}; observed={gate.value}; every Stage 2 "
                    "report stays provisional until Stage 1 passes"
                ),
            )
        )
    else:
        checks.append(
            PreflightCheck(
                check="stage1_continue_to_stage2",
                passed=gate is Stage1GateStatus.PASSED,
                detail=gate.value,
            )
        )

    canary = _optional_model(Stage2ModelCanaryRecord, canary_path_for(config, root))
    canary_ok = (
        canary is not None
        and canary.passed
        and canary.model_id == config.model.active_model_id
        and canary.revision == config.model.active_revision
        and canary.max_sequence_tokens >= config.qlora.max_sequence_tokens
        and canary.package_versions == package_versions()
    )
    checks.append(
        PreflightCheck(
            check="model_canary_passed",
            passed=canary_ok,
            detail=(
                "missing: run stage2-model-canary for the active model"
                if canary is None
                else (
                    f"passed={canary.passed}; model={canary.model_id}@{canary.revision[:8]}; "
                    f"peak_gib={canary.peak_gpu_memory_gib}; "
                    f"packages_match={canary.package_versions == package_versions()}"
                )
            ),
        )
    )

    gpu = gpu_identity()
    gpu_ok = config.hardware.expected_gpu_pattern.lower() in gpu.name.lower() and (
        gpu.total_memory_gib is not None
        and gpu.total_memory_gib >= config.hardware.min_total_vram_gib
    )
    checks.append(
        PreflightCheck(
            check="expected_cuda_gpu",
            passed=gpu_ok,
            detail=(
                f"gpu={gpu.name}; vram_gib={gpu.total_memory_gib}; driver={gpu.driver}; "
                f"torch_cuda={gpu.torch_cuda}"
            ),
        )
    )

    packages = package_versions()
    package_ok = all(name in packages for name in REQUIRED_PACKAGES)
    checks.append(
        PreflightCheck(
            check="stage2_packages_installed",
            passed=package_ok,
            detail=json.dumps(packages, sort_keys=True),
        )
    )
    kernels = {name: packages.get(name, "absent") for name in OPTIONAL_KERNEL_PACKAGES}
    delta_rule = "flash-linear-attention" in packages
    conv = "causal-conv1d" in packages
    active = [
        f"gated-delta-rule={'flash-linear-attention' if delta_rule else 'pytorch-fallback'}",
        f"causal-conv1d={'kernel' if conv else 'pytorch-fallback'}",
    ]
    checks.append(
        PreflightCheck(
            check="optional_linear_attention_kernels",
            passed=True,
            detail=(
                "informational: Gated DeltaNet kernel selection for this run; a fallback is "
                "correct but slower on long sequences and changes kernel numerics relative to "
                f"the other path. {'; '.join(active)}; "
                f"observed={json.dumps(kernels, sort_keys=True)}"
            ),
        )
    )

    os_ok = platform.system() == config.hardware.operating_system
    checks.append(
        PreflightCheck(
            check="expected_operating_system",
            passed=os_ok,
            detail=f"expected={config.hardware.operating_system}; observed={platform.system()}",
        )
    )

    if check_sandbox:
        sandbox_ok, sandbox_detail = _sandbox_status(config.sandbox)
        checks.append(
            PreflightCheck(
                check="docker_sandbox_linux_amd64", passed=sandbox_ok, detail=sandbox_detail
            )
        )

    report = Stage2PreflightReport(
        created_at=_now(),
        config_sha256=_sha(config_path.read_bytes()),
        host={
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        checks=tuple(checks),
        ready_for_dataset_freeze=split_ok and audit_ok,
        ready_for_training=all(check.passed for check in checks),
    )
    _write_model(output_path, report)
    return report


class Stage2TrainingManifest(StrictModel):
    schema_version: Literal[1] = 1
    harness_version: Literal["stage2-qlora-training-v2"] = TRAINING_HARNESS_VERSION
    run_id: str
    created_at: str
    config_path: str
    config_sha256: Sha256
    dataset_manifest_path: str
    dataset_manifest_sha256: Sha256
    preflight_path: str
    preflight_sha256: Sha256
    model_canary_path: str
    model_canary_sha256: Sha256
    stage1_report_sha256: Sha256 | None
    stage1_gate_status_at_authorization: Stage1GateStatus
    stage1_gate_override: str | None
    model: Stage2ModelSpec
    qlora: QLoRAConfig
    package_versions: dict[str, str]
    gpu_name: str
    gpu_total_memory_gib: float | None
    cuda_version: str
    test_split_access_during_training: Literal[False] = False
    checkpoint_selection_split: Literal["dev"] = "dev"
    renderer_adapter_enabled: Literal[False] = False
    only_planner_adapter_trainable: Literal[True] = True
    output_directory: str


def prepare_stage2_training_manifest(
    config_path: Path,
    repository_root: Path,
    dataset_manifest_path: Path,
    run_directory: Path,
    run_id: str,
    *,
    stage1_gate_override: str | None = None,
) -> Stage2TrainingManifest:
    """Freeze an authorized PC training run only after every data, gate, GPU, and package check."""
    _validate_run_id(run_id)
    config = load_stage2_config(config_path)
    root = repository_root.resolve()
    if run_directory.exists():
        raise Stage2Error(f"refusing to overwrite training run: {run_directory}")
    run_directory.mkdir(parents=True)
    preflight_path = run_directory / "preflight.json"
    preflight = audit_stage2_preflight(
        config_path, root, preflight_path, stage1_gate_override=stage1_gate_override
    )
    if not preflight.ready_for_training:
        failed = [check.check for check in preflight.checks if not check.passed]
        raise Stage2Error(f"Stage 2 training preflight failed: {failed}")
    dataset = _load(Stage2DatasetManifest, dataset_manifest_path)
    if dataset.config_sha256 != _sha(config_path.read_bytes()):
        raise Stage2Error("frozen dataset was produced from a different Stage 2 config")
    validate_dataset_files(dataset, dataset_manifest_path.parent)
    stage1_path = root / config.stage1_report_path
    stage1_sha = _sha(stage1_path.read_bytes()) if stage1_path.is_file() else None
    canary_path = canary_path_for(config, root)
    gpu = gpu_identity()
    manifest = Stage2TrainingManifest(
        run_id=run_id,
        created_at=_now(),
        config_path=_relative(config_path, root),
        config_sha256=_sha(config_path.read_bytes()),
        dataset_manifest_path=_relative(dataset_manifest_path, root),
        dataset_manifest_sha256=_sha(dataset_manifest_path.read_bytes()),
        preflight_path=_relative(preflight_path, root),
        preflight_sha256=_sha(preflight_path.read_bytes()),
        model_canary_path=_relative(canary_path, root),
        model_canary_sha256=_sha(canary_path.read_bytes()),
        stage1_report_sha256=stage1_sha,
        stage1_gate_status_at_authorization=stage1_gate_status(config, root),
        stage1_gate_override=stage1_gate_override,
        model=config.model,
        qlora=config.qlora,
        package_versions=package_versions(),
        gpu_name=gpu.name,
        gpu_total_memory_gib=gpu.total_memory_gib,
        cuda_version=f"runtime={gpu.torch_cuda}; driver={gpu.driver}",
        output_directory=_relative(run_directory / "checkpoints", root),
    )
    _write_model(run_directory / "manifest.json", manifest)
    return manifest


def validate_dataset_files(manifest: Stage2DatasetManifest, directory: Path) -> None:
    split_ids: dict[SplitName, set[str]] = {}
    for split_name, artifact in manifest.files.items():
        path = directory / artifact.path
        if not path.is_file() or _sha(path.read_bytes()) != artifact.sha256:
            raise Stage2Error(f"frozen {split_name.value} dataset hash mismatch")
        rows = load_frozen_rows(path)
        if len(rows) != artifact.rows or any(row.split is not split_name for row in rows):
            raise Stage2Error(f"frozen {split_name.value} dataset contents mismatch")
        split_ids[split_name] = {row.base_task_id for row in rows}
    if (
        split_ids[SplitName.TRAIN] & split_ids[SplitName.DEV]
        or split_ids[SplitName.TRAIN] & split_ids[SplitName.TEST]
        or split_ids[SplitName.DEV] & split_ids[SplitName.TEST]
    ):
        raise Stage2Error("base-task leakage exists across frozen dataset files")


def load_frozen_rows(path: Path) -> list[FrozenDatasetRow]:
    return [
        FrozenDatasetRow.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# --------------------------------------------------------------------------------------------
# Host inspection helpers
# --------------------------------------------------------------------------------------------


class GpuIdentity(StrictModel):
    name: str
    total_memory_gib: float | None
    driver: str
    torch_cuda: str


def gpu_identity() -> GpuIdentity:
    try:
        process = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return GpuIdentity(
            name="unavailable",
            total_memory_gib=None,
            driver="unavailable",
            torch_cuda=_torch_cuda(),
        )
    if process.returncode != 0 or not process.stdout.strip():
        return GpuIdentity(
            name="unavailable",
            total_memory_gib=None,
            driver="unavailable",
            torch_cuda=_torch_cuda(),
        )
    parts = [part.strip() for part in process.stdout.splitlines()[0].split(",")]
    name = parts[0] if parts else "unavailable"
    memory_gib: float | None = None
    if len(parts) > 1:
        match = re.match(r"(\d+(?:\.\d+)?)\s*MiB", parts[1])
        if match:
            memory_gib = round(float(match.group(1)) / 1024, 2)
    driver = parts[2] if len(parts) > 2 else "unknown"
    return GpuIdentity(
        name=name, total_memory_gib=memory_gib, driver=driver, torch_cuda=_torch_cuda()
    )


def _torch_cuda() -> str:
    try:
        import torch

        return str(torch.version.cuda or "none")
    except ImportError:
        return "torch-not-installed"


def package_versions() -> dict[str, str]:
    """Exact interpreter and package versions; canary and preflight must agree on every one."""
    versions: dict[str, str] = {"python": platform.python_version()}
    for name in (*REQUIRED_PACKAGES, *OPTIONAL_KERNEL_PACKAGES):
        with suppress(importlib.metadata.PackageNotFoundError):
            versions[name] = importlib.metadata.version(name)
    return versions


def _sandbox_status(config: SandboxConfig) -> tuple[bool, str]:
    from sable_ir.harness import DockerSandbox, HarnessError

    try:
        DockerSandbox(config).ensure_available()
    except HarnessError as error:
        return False, str(error)
    return True, f"image={config.image}; platform={config.platform}"


# --------------------------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------------------------


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
            f"each paraphrase variant requires A/B structured/freeform rows: {incomplete[:3]}"
        )
    plan_by_cell: dict[tuple[str, PolicyValue, Stage1PlanFormat], str] = {}
    for row in rows:
        cell = (row.base_task_id, row.policy, row.plan_format)
        if plan_by_cell.setdefault(cell, row.completion) != row.completion:
            raise Stage2Error(f"paraphrase rows of one cell must share one reference plan: {cell}")
    for (task_id, plan_format), completions in _group_completions(rows).items():
        if completions[PolicyValue.A] == completions[PolicyValue.B]:
            raise Stage2Error(f"A and B reference plans are identical: {task_id}/{plan_format}")


def _group_completions(
    rows: tuple[ReferencePlanRow, ...],
) -> dict[tuple[str, Stage1PlanFormat], dict[PolicyValue, str]]:
    grouped: dict[tuple[str, Stage1PlanFormat], dict[PolicyValue, str]] = {}
    for row in rows:
        grouped.setdefault((row.base_task_id, row.plan_format), {})[row.policy] = row.completion
    return grouped


def _load_tasks(config: Stage2Config, root: Path) -> dict[str, tuple[str, TaskSpec]]:
    tasks: dict[str, tuple[str, TaskSpec]] = {}
    for relative in config.task_paths:
        task = load_task(root / relative)
        if task.id in tasks:
            raise Stage2Error(f"duplicate task id: {task.id}")
        tasks[task.id] = (relative, task)
    return tasks


def _validate_run_id(run_id: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", run_id):
        raise Stage2Error("run IDs must be 1-64 safe filename characters")


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise Stage2Error(f"artifact must live inside the repository: {path}")
    return resolved.relative_to(root).as_posix()


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
    return _sha(model.model_dump_json().encode("utf-8"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_model(path: Path, model: StrictModel) -> None:
    _write_new(path, model.model_dump_json(indent=2) + "\n")


def _write_new(path: Path, payload: str) -> None:
    """Create-only UTF-8 write with LF newlines so hashes match on Windows and POSIX alike."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
