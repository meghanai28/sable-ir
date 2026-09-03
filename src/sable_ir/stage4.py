"""Stage 4 single-position policy-subspace intervention contracts."""

from __future__ import annotations

import hashlib
import os
import tomllib
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, TypeVar

from pydantic import Field, ValidationError, model_validator

from sable_ir.config import load_task
from sable_ir.harness import EvaluationHarness, EvaluationResult, SandboxBackend
from sable_ir.schema import PolicyValue, SandboxConfig, StrictModel, TestSuiteKind
from sable_ir.stage1 import build_renderer_prompt
from sable_ir.stage1_analysis import PolicyVisibility
from sable_ir.stage2 import DesignMode, SplitName, Stage2ModelSpec, load_stage2_config
from sable_ir.stage2_local import AdapterRef, GenerationStatus, LocalGeneration
from sable_ir.stage3 import (
    BoundaryState,
    Stage3Dataset,
    Stage3DatasetRow,
    load_activation_manifest,
    load_stage3_dataset,
)
from sable_ir.stage3_analysis import (
    Stage3Heldout,
    Stage3ProbeFit,
    Stage3Report,
    Stage3Selection,
    load_plan_texts,
)

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)
STAGE4_HARNESS_VERSION: Literal["stage4-causal-subspace-v2"] = "stage4-causal-subspace-v2"


class Stage4Error(RuntimeError):
    """Stage 4 authorization, provenance, intervention, or report error."""


class DirectionKind(StrEnum):
    POLICY_ORIENTATION = "policy_orientation"
    RANDOM_ORTHOGONAL = "random_orthogonal"
    UNRELATED_SECURITY_FACT = "unrelated_security_fact"
    PARAPHRASE_IDENTITY = "paraphrase_identity"
    LEXICAL_FRAMING = "lexical_framing"
    UNRELATED_TASK_VALUE = "unrelated_task_value"
    PREREGISTERED_EARLY_LAYER = "preregistered_early_layer"
    FULL_VECTOR_SAME_TASK = "full_vector_same_task"


class DirectionRole(StrEnum):
    TARGET = "target"
    MATCHED_NULL_CONTROL = "matched_null_control"
    VALUE_TRANSFER_DIAGNOSTIC = "value_transfer_diagnostic"
    LOCALIZATION_DIAGNOSTIC = "localization_diagnostic"
    POSITIVE_ORACLE = "positive_oracle"


MATCHED_NULL_CONTROLS = frozenset(
    {
        DirectionKind.RANDOM_ORTHOGONAL,
        DirectionKind.UNRELATED_SECURITY_FACT,
        DirectionKind.PARAPHRASE_IDENTITY,
        DirectionKind.LEXICAL_FRAMING,
    }
)


def direction_role(kind: DirectionKind) -> DirectionRole:
    if kind is DirectionKind.POLICY_ORIENTATION:
        return DirectionRole.TARGET
    if kind in MATCHED_NULL_CONTROLS:
        return DirectionRole.MATCHED_NULL_CONTROL
    if kind is DirectionKind.UNRELATED_TASK_VALUE:
        return DirectionRole.VALUE_TRANSFER_DIAGNOSTIC
    if kind is DirectionKind.PREREGISTERED_EARLY_LAYER:
        return DirectionRole.LOCALIZATION_DIAGNOSTIC
    return DirectionRole.POSITIVE_ORACLE


class InterventionMode(StrEnum):
    SINGLE_POSITION_SUBSPACE = "single_position_causal_subspace"
    RECURRENT_STEERING = "recurrent_steering"
    CONTRADICTORY_TEXT = "contradictory_text"


class Stage4Thresholds(StrictModel):
    sanity_min_ab_js_divergence: float = Field(default=0.001, gt=0)
    sanity_min_teacher_forced_log_odds_gap: float = Field(default=0.05, gt=0)
    target_functionality_max_lost_outputs: Literal[1] = 1
    full_samples_per_condition: int = Field(default=16, ge=8, le=32)


class Stage4Config(StrictModel):
    schema_version: Literal[1] = 1
    artifacts_dir: str = "artifacts/stage4"
    stage2_config_path: str
    stage3_dataset_path: str
    stage3_selection_path: str
    stage3_heldout_path: str
    stage3_report_path: str
    recipient_audit_path: str
    divergence_spec_path: str
    dev_task_id: str
    heldout_task_id: str
    early_layer: int = Field(ge=0)
    thresholds: Stage4Thresholds = Stage4Thresholds()

    @model_validator(mode="after")
    def validate_paths(self) -> Stage4Config:
        for name in (
            "artifacts_dir",
            "stage2_config_path",
            "stage3_dataset_path",
            "stage3_selection_path",
            "stage3_heldout_path",
            "stage3_report_path",
            "recipient_audit_path",
            "divergence_spec_path",
        ):
            value = getattr(self, name)
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "\\" in value:
                raise ValueError(f"{name} must be a repository-relative POSIX path")
        if self.dev_task_id == self.heldout_task_id:
            raise ValueError("Stage 4 development and held-out tasks must differ")
        return self


class DivergenceTask(StrictModel):
    common_code_prefix: str = Field(min_length=1)
    policy_a_continuation: str = Field(min_length=1)
    policy_b_continuation: str = Field(min_length=1)
    policy_relevant_tokens: tuple[str, ...] = Field(min_length=1)


class DivergenceSpec(StrictModel):
    schema_version: Literal[1] = 1
    created_before_stage4_results: Literal[True] = True
    tasks: dict[str, DivergenceTask]


class Stage4ConfigSummary(StrictModel):
    valid: Literal[True] = True
    dev_task: str
    heldout_task: str
    early_layer: int
    samples_per_condition: int
    conditions: int
    total_full_jobs: int
    divergence_spec_sha256: Sha256
    evidence_scope: Literal["one-heldout-task-case-study"] = "one-heldout-task-case-study"


class RecipientCandidate(StrictModel):
    job_id: str
    task_id: str
    split: SplitName
    assigned_policy: PolicyValue
    paraphrase_set: str
    plan_format: str
    concision: str
    policy_visibility: PolicyVisibility
    plan_tokens: int
    plan_sha256: Sha256
    plan: str


class RecipientSelection(StrictModel):
    split: SplitName
    task_id: str
    explicit_a_job_id: str | None = None
    explicit_b_job_id: str | None = None
    omitted_recipient_job_id: str | None = None
    audited_without_generated_code_or_test_outcomes: Literal[True] | None = None
    same_surface_request: bool | None = None
    omitted_plan_functionally_meaningful: bool | None = None
    omitted_plan_neutral_between_a_and_b: bool | None = None
    format_length_and_nontarget_information_matched_where_possible: bool | None = None
    notes: str | None = None

    @property
    def complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.explicit_a_job_id,
                self.explicit_b_job_id,
                self.omitted_recipient_job_id,
                self.audited_without_generated_code_or_test_outcomes,
                self.same_surface_request,
                self.omitted_plan_functionally_meaningful,
                self.omitted_plan_neutral_between_a_and_b,
                self.format_length_and_nontarget_information_matched_where_possible,
            )
        )


class Stage4RecipientAudit(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    stage3_dataset_sha256: Sha256
    stage3_report_sha256: Sha256
    instructions: str
    candidates: tuple[RecipientCandidate, ...]
    selections: tuple[RecipientSelection, ...]
    reviewer: str | None = None
    completed_at: str | None = None

    @model_validator(mode="after")
    def validate_completion(self) -> Stage4RecipientAudit:
        complete = [row.complete for row in self.selections]
        if any(complete) and not all(complete):
            raise ValueError("recipient audit cannot mix complete and incomplete selections")
        if all(complete) != bool(self.reviewer and self.completed_at):
            raise ValueError("recipient audit completion requires reviewer and completed_at")
        return self


class SelectedRecipient(StrictModel):
    split: SplitName
    task_id: str
    explicit_a: RecipientCandidate
    explicit_b: RecipientCandidate
    omitted: RecipientCandidate


class DirectionArtifact(StrictModel):
    kind: DirectionKind
    role: DirectionRole
    layer: int
    path: str | None
    sha256: Sha256 | None
    derivation: str
    centroids: tuple[float, float] | None = None

    @model_validator(mode="after")
    def validate_role(self) -> DirectionArtifact:
        if self.role is not direction_role(self.kind):
            raise ValueError(f"{self.kind.value} must have role {direction_role(self.kind).value}")
        return self


class Stage4ExperimentManifest(StrictModel):
    schema_version: Literal[1] = 1
    harness_version: Literal["stage4-causal-subspace-v2"] = STAGE4_HARNESS_VERSION
    run_id: str
    created_at: str
    design_mode: DesignMode
    pilot: bool
    config_path: str
    config_sha256: Sha256
    stage2_config_path: str
    stage2_config_sha256: Sha256
    stage3_activation_manifest_path: str
    stage3_activation_manifest_sha256: Sha256
    stage3_dataset_sha256: Sha256
    stage3_selection_sha256: Sha256
    stage3_heldout_sha256: Sha256
    stage3_report_sha256: Sha256
    recipient_audit_sha256: Sha256
    model: Stage2ModelSpec
    planner_adapter: AdapterRef
    renderer_adapter_enabled: Literal[False] = False
    selected_layer: int
    centroids: tuple[float, float]
    direction_artifacts: tuple[DirectionArtifact, ...]
    strength_multipliers: tuple[float, ...]
    recipients: tuple[SelectedRecipient, ...]
    unrelated_security_fact_a: str
    unrelated_security_fact_b: str
    sandbox: SandboxConfig

    @model_validator(mode="after")
    def validate_design(self) -> Stage4ExperimentManifest:
        if {row.kind for row in self.direction_artifacts} != set(DirectionKind):
            raise ValueError("experiment must declare every target/control direction")
        if {row.split for row in self.recipients} != {SplitName.DEV, SplitName.TEST}:
            raise ValueError("experiment requires one development and one test recipient")
        if len(self.recipients) != 2:
            raise ValueError("experiment requires exactly two recipient triplets")
        if self.centroids[0] == self.centroids[1]:
            raise ValueError("policy centroids must differ")
        if not self.strength_multipliers or 1.0 not in self.strength_multipliers:
            raise ValueError("strengths must include the exact centroid edit at 1.0")
        return self


class Stage4DirectionSet(StrictModel):
    """Runtime-materialized intervention vectors bound to one frozen experiment."""

    schema_version: Literal[1] = 1
    created_at: str
    experiment_manifest_sha256: Sha256
    artifacts: tuple[DirectionArtifact, ...]
    target_random_absolute_dot: float = Field(ge=0)
    decoder_block_container_module: str
    expected_num_layers: int = Field(gt=1)
    hook_location: Literal["post_block_output"] = "post_block_output"
    equivalent_strength_rule: Literal["target_centroid_gap"] = "target_centroid_gap"
    renderer_adapter_enabled: Literal[False] = False

    @model_validator(mode="after")
    def validate_complete(self) -> Stage4DirectionSet:
        if {row.kind for row in self.artifacts} != set(DirectionKind):
            raise ValueError("direction set must contain every target/control direction")
        if any(row.path is None or row.sha256 is None for row in self.artifacts):
            raise ValueError("every materialized direction needs a path and hash")
        if self.target_random_absolute_dot > 1e-5:
            raise ValueError("random control is not orthogonal to the target direction")
        return self


class SanityPairResult(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    experiment_manifest_sha256: Sha256
    direction_set_sha256: Sha256
    divergence_spec_sha256: Sha256
    prompt_sha256: Sha256
    task_id: str
    split: Literal[SplitName.DEV] = SplitName.DEV
    direction_kind: DirectionKind
    strength_multiplier: float
    unpatched_to_a_kl: float = Field(ge=0)
    unpatched_to_b_kl: float = Field(ge=0)
    a_vs_b_js_divergence: float = Field(ge=0)
    teacher_forced_a_minus_b_log_odds_gap: float
    policy_relevant_token_logit_changes: dict[str, float]
    raw_distribution_path: str
    raw_distribution_sha256: Sha256


class Stage4SanitySelection(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    experiment_manifest_sha256: Sha256
    sanity_result_sha256s: dict[str, Sha256]
    direction_set_sha256: Sha256
    divergence_spec_sha256: Sha256
    prompt_sha256: Sha256
    selected_strength_multiplier: float | None
    target_ab_js_divergence: float | None
    strongest_control_ab_js_divergence: float | None
    target_teacher_forced_log_odds_gap: float | None
    passed: bool
    status: Literal["passed", "sanity_check_failed"]
    rationale: str
    development_only: Literal[True] = True


class FullRunJob(StrictModel):
    job_id: str
    task_id: str
    split: Literal[SplitName.TEST] = SplitName.TEST
    direction_kind: DirectionKind | None
    target_policy: PolicyValue | None
    mode: InterventionMode
    strength_multiplier: float
    sample_index: int
    seed: int
    prompt: str
    prompt_sha256: Sha256
    candidate_path: str
    result_path: str


class HookSpecification(StrictModel):
    module: str
    layer: int = Field(ge=0)
    location: Literal["post_block_output"] = "post_block_output"
    token_marker: Literal["END_PLAN"] = "END_PLAN"
    token_index: int = Field(ge=0)
    phase: Literal["prompt_prefill"] = "prompt_prefill"
    downstream_layers_receiving_edit: int = Field(ge=1)


class Stage4FullRunManifest(StrictModel):
    schema_version: Literal[1] = 1
    harness_version: Literal["stage4-causal-subspace-v2"] = STAGE4_HARNESS_VERSION
    run_id: str
    created_at: str
    experiment_manifest_path: str
    experiment_manifest_sha256: Sha256
    sanity_selection_sha256: Sha256
    direction_set_path: str
    direction_set_sha256: Sha256
    resolved_direction_artifacts: tuple[DirectionArtifact, ...]
    selected_strength_multiplier: float
    samples_per_condition: int
    sandbox: SandboxConfig
    jobs: tuple[FullRunJob, ...]
    hook_by_direction: dict[DirectionKind, HookSpecification]
    paired_seed_by_sample_index: dict[int, int]
    primary_mode: Literal[InterventionMode.SINGLE_POSITION_SUBSPACE] = (
        InterventionMode.SINGLE_POSITION_SUBSPACE
    )
    recurrent_steering_requires_primary_washout: Literal[True] = True
    contradictory_text_requires_primary_completion: Literal[True] = True

    @model_validator(mode="after")
    def validate_matrix(self) -> Stage4FullRunManifest:
        if len({job.job_id for job in self.jobs}) != len(self.jobs):
            raise ValueError("full-run job ids must be unique")
        counts: dict[tuple[DirectionKind | None, PolicyValue | None], int] = defaultdict(int)
        for job in self.jobs:
            if (job.direction_kind is None) != (job.target_policy is None):
                raise ValueError("only unpatched jobs may omit both direction and target")
            counts[(job.direction_kind, job.target_policy)] += 1
        expected = {(None, None)} | {
            (kind, policy) for kind in DirectionKind for policy in PolicyValue
        }
        if set(counts) != expected or any(
            count != self.samples_per_condition for count in counts.values()
        ):
            raise ValueError("full-run matrix must cover all 17 conditions equally")
        if set(self.hook_by_direction) != set(DirectionKind):
            raise ValueError("full run must freeze one exact hook for every direction")
        if set(self.paired_seed_by_sample_index) != set(range(self.samples_per_condition)):
            raise ValueError("paired seed map must cover every sample index")
        for sample in range(self.samples_per_condition):
            seeds = {job.seed for job in self.jobs if job.sample_index == sample}
            if seeds != {self.paired_seed_by_sample_index[sample]}:
                raise ValueError("all conditions must share the fixed seed for each sample index")
        by_kind = {row.kind: row for row in self.resolved_direction_artifacts}
        for kind, hook in self.hook_by_direction.items():
            if hook.layer != by_kind[kind].layer:
                raise ValueError("hook layer must equal its frozen direction layer")
        return self


class Stage4GenerationRecord(StrictModel):
    schema_version: Literal[1] = 1
    job_id: str
    prompt_sha256: Sha256
    generation: LocalGeneration
    status: GenerationStatus
    raw_text_sha256: Sha256
    candidate_sha256: Sha256 | None
    extraction: str | None
    error: str | None
    intervention_applied: bool
    edited_positions: int
    orthogonal_component_changed_max_abs: float | None
    direction_sha256: Sha256 | None
    projection_before: float | None
    projection_after: float | None
    edit_l2_norm: float | None
    hook: HookSpecification | None
    observed_end_plan_token_index: int | None
    intervention_phase: Literal["prompt_prefill"] | None
    downstream_layers_receiving_edit: int | None
    zero_strength_logits_identical: bool | None


class Stage4EvaluationArtifact(StrictModel):
    schema_version: Literal[1] = 1
    job_id: str
    manifest_sha256: Sha256
    result_sha256: Sha256
    candidate_sha256: Sha256 | None
    evaluation: EvaluationResult | None


class ConditionOutcome(StrictModel):
    direction_kind: DirectionKind | None
    target_policy: PolicyValue | None
    samples: int
    functional_count: int
    functional_rate: float
    policy_a_and_functional_rate: float
    policy_b_and_functional_rate: float


class Stage4Report(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    run_id: str
    full_run_manifest_sha256: Sha256
    complete: bool
    status: Literal["complete", "incomplete", "invalid_task_or_tests"]
    evaluated_jobs: int
    expected_jobs: int
    heldout_tasks: tuple[str, ...]
    outcomes: tuple[ConditionOutcome, ...]
    a_injection_shift: float | None
    b_injection_shift: float | None
    strongest_matched_control_shift: float | None
    matched_null_control_kinds: tuple[DirectionKind, ...]
    diagnostic_kinds_excluded_from_success: tuple[DirectionKind, ...]
    bidirectional: bool
    exceeds_every_matched_control: bool
    target_a_functional_outputs_lost: int | None
    target_b_functional_outputs_lost: int | None
    functionality_within_one_paired_sample: bool
    survives_paraphrase_set2: bool
    functional_outputs_passing_both_suites: int
    causal_success: bool
    evidence_scope: Literal["heldout_task_case_study"] = "heldout_task_case_study"
    cross_task_generalization_claim: Literal[False] = False
    recurrent_steering_result_must_be_reported_separately: Literal[True] = True
    intervention_name: Literal["single-position causal subspace intervention"] = (
        "single-position causal subspace intervention"
    )


def load_stage4_config(path: Path) -> Stage4Config:
    try:
        return Stage4Config.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise Stage4Error(f"cannot load Stage 4 config: {error}") from error


def validate_stage4_config(config_path: Path, repository_root: Path) -> Stage4ConfigSummary:
    config = load_stage4_config(config_path)
    root = repository_root.resolve()
    stage2 = load_stage2_config(root / config.stage2_config_path)
    tasks = {load_task(root / path).id for path in stage2.task_paths}
    if config.dev_task_id not in tasks or config.heldout_task_id not in tasks:
        raise Stage4Error("Stage 4 dev/held-out tasks must exist in the Stage 2 task set")
    divergence_path = root / config.divergence_spec_path
    try:
        divergence = DivergenceSpec.model_validate_json(divergence_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise Stage4Error(f"cannot load the Stage 4 divergence spec: {error}") from error
    if set(divergence.tasks) != {config.dev_task_id, config.heldout_task_id}:
        raise Stage4Error("divergence spec must cover exactly the Stage 4 dev and held-out tasks")
    conditions = 1 + 2 * len(DirectionKind)
    return Stage4ConfigSummary(
        dev_task=config.dev_task_id,
        heldout_task=config.heldout_task_id,
        early_layer=config.early_layer,
        samples_per_condition=config.thresholds.full_samples_per_condition,
        conditions=conditions,
        total_full_jobs=conditions * config.thresholds.full_samples_per_condition,
        divergence_spec_sha256=_sha(divergence_path.read_bytes()),
    )


def prepare_recipient_audit(
    config_path: Path, repository_root: Path, output: Path
) -> Stage4RecipientAudit:
    config = load_stage4_config(config_path)
    root = repository_root.resolve()
    dataset_path = root / config.stage3_dataset_path
    report_path = root / config.stage3_report_path
    dataset = load_stage3_dataset(dataset_path)
    report = _load(Stage3Report, report_path)
    _require_stage3_authorization(config, root, dataset, report)
    plans = load_plan_texts(dataset, root)
    wanted = {
        SplitName.DEV: config.dev_task_id,
        SplitName.TEST: config.heldout_task_id,
    }
    candidates: list[RecipientCandidate] = []
    for row in dataset.rows:
        if wanted.get(row.split) != row.task_id or row.plan_sha256 is None:
            continue
        if row.policy_visibility is None or row.plan_tokens is None:
            continue
        candidates.append(_recipient_candidate(row, plans[row.job_id]))
    for split, task_id in wanted.items():
        rows = [row for row in candidates if row.split is split]
        if not any(_is_explicit(row, PolicyValue.A) for row in rows):
            raise Stage4Error(f"no explicit-A set-2 full-plan candidate for {task_id}")
        if not any(_is_explicit(row, PolicyValue.B) for row in rows):
            raise Stage4Error(f"no explicit-B set-2 full-plan candidate for {task_id}")
        if not any(_is_omitted(row) for row in rows):
            raise Stage4Error(f"no naturally compressed omitted/blurred candidate for {task_id}")
    audit = Stage4RecipientAudit(
        created_at=_now(),
        stage3_dataset_sha256=_sha(dataset_path.read_bytes()),
        stage3_report_sha256=_sha(report_path.read_bytes()),
        instructions=(
            "Behavior-blinded recipient audit: do not view generated code or test outcomes. For "
            "development and held-out tasks, select set-2 full explicit A/B sources and one "
            "naturally generated concise/minimal omitted-or-blurred recipient. Confirm that the "
            "recipient is meaningful, neutral rather than contradictory, shares the surface "
            "request, and is matched on format/length/non-target content where possible."
        ),
        candidates=tuple(candidates),
        selections=tuple(
            RecipientSelection(split=split, task_id=task_id) for split, task_id in wanted.items()
        ),
    )
    _write_model(output, audit)
    return audit


def prepare_stage4_experiment(
    config_path: Path, repository_root: Path, run_directory: Path, run_id: str
) -> Stage4ExperimentManifest:
    config = load_stage4_config(config_path)
    root = repository_root.resolve()
    dataset_path = root / config.stage3_dataset_path
    selection_path = root / config.stage3_selection_path
    heldout_path = root / config.stage3_heldout_path
    report_path = root / config.stage3_report_path
    audit_path = root / config.recipient_audit_path
    dataset = load_stage3_dataset(dataset_path)
    selection = _load(Stage3Selection, selection_path)
    heldout = _load(Stage3Heldout, heldout_path)
    report = _load(Stage3Report, report_path)
    _require_stage3_authorization(config, root, dataset, report)
    if heldout.selection_sha256 != _sha(selection_path.read_bytes()):
        raise Stage4Error("Stage 3 held-out results reference another selection")
    recipients = _validate_recipient_audit(audit_path, dataset_path, report_path, root)
    layer = selection.direction_layer[BoundaryState.RENDERER_INGESTION]
    direction_sha = selection.direction_sha256[BoundaryState.RENDERER_INGESTION]
    centroids = selection.centroids[BoundaryState.RENDERER_INGESTION]
    if layer is None or direction_sha is None or centroids is None:
        raise Stage4Error("Stage 3 did not freeze a renderer-ingestion direction and centroids")
    direction_path = selection_path.parent / "directions" / f"renderer_ingestion__L{layer:02d}.npy"
    if _sha(direction_path.read_bytes()) != direction_sha:
        raise Stage4Error("renderer-ingestion direction hash mismatch")
    if run_directory.exists():
        raise Stage4Error(f"refusing to overwrite Stage 4 run: {run_directory}")
    run_directory.mkdir(parents=True)
    activation_manifest_path = root / dataset.activation_manifest_path
    stage3_manifest = load_activation_manifest(activation_manifest_path)
    stage2_path = root / config.stage2_config_path
    stage2 = load_stage2_config(stage2_path)
    controls = _direction_artifacts(
        root,
        selection,
        selection_path,
        layer,
        config.early_layer,
        run_directory,
    )
    manifest = Stage4ExperimentManifest(
        run_id=run_id,
        created_at=_now(),
        design_mode=dataset.design_mode,
        pilot=dataset.pilot,
        config_path=_relative(config_path, root),
        config_sha256=_sha(config_path.read_bytes()),
        stage2_config_path=config.stage2_config_path,
        stage2_config_sha256=_sha(stage2_path.read_bytes()),
        stage3_activation_manifest_path=dataset.activation_manifest_path,
        stage3_activation_manifest_sha256=_sha(activation_manifest_path.read_bytes()),
        stage3_dataset_sha256=_sha(dataset_path.read_bytes()),
        stage3_selection_sha256=_sha(selection_path.read_bytes()),
        stage3_heldout_sha256=_sha(heldout_path.read_bytes()),
        stage3_report_sha256=_sha(report_path.read_bytes()),
        recipient_audit_sha256=_sha(audit_path.read_bytes()),
        model=stage2.model,
        planner_adapter=stage3_manifest.planner_adapter,
        selected_layer=layer,
        centroids=centroids,
        direction_artifacts=tuple(
            [
                DirectionArtifact(
                    kind=DirectionKind.POLICY_ORIENTATION,
                    role=direction_role(DirectionKind.POLICY_ORIENTATION),
                    layer=layer,
                    path=_relative(direction_path, root),
                    sha256=direction_sha,
                    derivation=(
                        "task-balanced training-task A/B difference means; paraphrase set 1"
                    ),
                    centroids=centroids,
                )
            ]
            + controls
        ),
        strength_multipliers=selection.strength_multipliers,
        recipients=recipients,
        unrelated_security_fact_a=(
            "Authentication sessions must use Secure, HttpOnly, and SameSite cookies, and "
            "the application must rotate the session identifier after login or privilege changes."
        ),
        unrelated_security_fact_b=(
            "Authentication sessions may use cookies without Secure, HttpOnly, or SameSite "
            "attributes, and may retain the same session identifier after login or privilege "
            "changes."
        ),
        sandbox=stage2.sandbox,
    )
    _write_model(run_directory / "manifest.json", manifest)
    return manifest


def select_stage4_sanity(
    experiment_manifest_path: Path,
    sanity_result_paths: tuple[Path, ...],
    repository_root: Path,
    output: Path,
) -> Stage4SanitySelection:
    manifest = _load(Stage4ExperimentManifest, experiment_manifest_path)
    config = load_stage4_config(repository_root.resolve() / manifest.config_path)
    records = [_load(SanityPairResult, path) for path in sanity_result_paths]
    experiment_sha = _sha(experiment_manifest_path.read_bytes())
    if not records or any(
        row.run_id != manifest.run_id or row.experiment_manifest_sha256 != experiment_sha
        for row in records
    ):
        raise Stage4Error("sanity results do not cover this experiment")
    keys = {(row.direction_kind, row.strength_multiplier) for row in records}
    expected = {
        (kind, strength)
        for kind in (DirectionKind.POLICY_ORIENTATION, *sorted(MATCHED_NULL_CONTROLS))
        for strength in manifest.strength_multipliers
    }
    if keys != expected or len(records) != len(expected):
        raise Stage4Error(
            "sanity selection requires exactly the target and four matched null controls at "
            "every strength; diagnostics and the held-out oracle are forbidden"
        )
    for field in ("direction_set_sha256", "divergence_spec_sha256", "prompt_sha256"):
        if len({getattr(row, field) for row in records}) != 1:
            raise Stage4Error(f"sanity results disagree on {field}")
    root = repository_root.resolve()
    for row in records:
        raw = root / row.raw_distribution_path
        if _sha(raw.read_bytes()) != row.raw_distribution_sha256:
            raise Stage4Error(f"raw sanity distribution hash mismatch: {row.direction_kind}")
    by_strength: dict[float, list[SanityPairResult]] = defaultdict(list)
    for row in records:
        by_strength[row.strength_multiplier].append(row)
    eligible: list[tuple[float, SanityPairResult, float]] = []
    for strength in manifest.strength_multipliers:
        rows = by_strength.get(strength, [])
        target = next(
            (row for row in rows if row.direction_kind is DirectionKind.POLICY_ORIENTATION),
            None,
        )
        controls = [
            row.a_vs_b_js_divergence for row in rows if row.direction_kind in MATCHED_NULL_CONTROLS
        ]
        if target is None or not controls:
            continue
        strongest = max(controls)
        if (
            target.a_vs_b_js_divergence >= config.thresholds.sanity_min_ab_js_divergence
            and target.teacher_forced_a_minus_b_log_odds_gap
            >= config.thresholds.sanity_min_teacher_forced_log_odds_gap
            and target.a_vs_b_js_divergence > strongest
        ):
            eligible.append((strength, target, strongest))
    selected = min(eligible, key=lambda item: item[0]) if eligible else None
    result = Stage4SanitySelection(
        created_at=_now(),
        experiment_manifest_sha256=_sha(experiment_manifest_path.read_bytes()),
        sanity_result_sha256s={
            path.as_posix(): _sha(path.read_bytes()) for path in sanity_result_paths
        },
        direction_set_sha256=records[0].direction_set_sha256,
        divergence_spec_sha256=records[0].divergence_spec_sha256,
        prompt_sha256=records[0].prompt_sha256,
        selected_strength_multiplier=None if selected is None else selected[0],
        target_ab_js_divergence=None if selected is None else selected[1].a_vs_b_js_divergence,
        strongest_control_ab_js_divergence=None if selected is None else selected[2],
        target_teacher_forced_log_odds_gap=(
            None if selected is None else selected[1].teacher_forced_a_minus_b_log_odds_gap
        ),
        passed=selected is not None,
        status="passed" if selected is not None else "sanity_check_failed",
        rationale=(
            "smallest preregistered development strength whose A/B distribution difference "
            "exceeds every matched control"
            if selected is not None
            else "no preregistered development strength exceeded the matched controls; do not "
            "sample complete held-out code"
        ),
    )
    _write_model(output, result)
    return result


def prepare_stage4_full_run(
    experiment_manifest_path: Path,
    sanity_selection_path: Path,
    direction_set_path: Path,
    repository_root: Path,
    run_directory: Path,
    run_id: str,
) -> Stage4FullRunManifest:
    root = repository_root.resolve()
    experiment = _load(Stage4ExperimentManifest, experiment_manifest_path)
    selection = _load(Stage4SanitySelection, sanity_selection_path)
    if selection.experiment_manifest_sha256 != _sha(experiment_manifest_path.read_bytes()):
        raise Stage4Error("sanity selection references another experiment")
    if not selection.passed or selection.selected_strength_multiplier is None:
        raise Stage4Error("full code sampling is blocked by the development sanity check")
    directions = _load(Stage4DirectionSet, direction_set_path)
    if directions.experiment_manifest_sha256 != _sha(experiment_manifest_path.read_bytes()):
        raise Stage4Error("materialized directions reference another experiment")
    if selection.direction_set_sha256 != _sha(direction_set_path.read_bytes()):
        raise Stage4Error("sanity selection was produced with another direction set")
    config = load_stage4_config(root / experiment.config_path)
    recipient = next(row for row in experiment.recipients if row.split is SplitName.TEST)
    task = load_task(root / _task_path_for(experiment, root, recipient.task_id))
    prompt = build_renderer_prompt(task.surface_request, recipient.omitted.plan)
    stage3_dataset = load_stage3_dataset(root / config.stage3_dataset_path)
    recipient_row = next(
        row for row in stage3_dataset.rows if row.job_id == recipient.omitted.job_id
    )
    state = recipient_row.states.get(BoundaryState.RENDERER_INGESTION)
    if state is None:
        raise Stage4Error("selected recipient lacks a renderer-ingestion END_PLAN state")
    by_kind = {row.kind: row for row in directions.artifacts}
    hook_by_direction = {
        kind: HookSpecification(
            module=f"{directions.decoder_block_container_module}.{artifact.layer}",
            layer=artifact.layer,
            token_index=state.token_index,
            downstream_layers_receiving_edit=(directions.expected_num_layers - artifact.layer - 1),
        )
        for kind, artifact in by_kind.items()
    }
    paired_seeds = {
        sample: _seed(experiment.run_id, f"{recipient.task_id}:paired:{sample}")
        for sample in range(config.thresholds.full_samples_per_condition)
    }
    conditions: list[tuple[DirectionKind | None, PolicyValue | None]] = [(None, None)]
    for kind in DirectionKind:
        conditions.extend((kind, policy) for policy in PolicyValue)
    jobs: list[FullRunJob] = []
    for direction_kind, policy in conditions:
        if direction_kind is not None and policy is None:
            raise Stage4Error("an intervention condition requires a target policy")
        if direction_kind is None:
            condition = "unpatched"
        else:
            assert policy is not None
            condition = f"{direction_kind.value}_{policy.value.lower()}"
        for sample in range(config.thresholds.full_samples_per_condition):
            job_id = f"{recipient.task_id}__{condition}__s{sample:02d}"
            jobs.append(
                FullRunJob(
                    job_id=job_id,
                    task_id=recipient.task_id,
                    direction_kind=direction_kind,
                    target_policy=policy,
                    mode=InterventionMode.SINGLE_POSITION_SUBSPACE,
                    strength_multiplier=selection.selected_strength_multiplier,
                    sample_index=sample,
                    seed=paired_seeds[sample],
                    prompt=prompt,
                    prompt_sha256=_sha(prompt.encode()),
                    candidate_path=f"jobs/{job_id}/candidate.py",
                    result_path=f"jobs/{job_id}/result.json",
                )
            )
    if run_directory.exists():
        raise Stage4Error(f"refusing to overwrite Stage 4 full run: {run_directory}")
    run_directory.mkdir(parents=True)
    manifest = Stage4FullRunManifest(
        run_id=run_id,
        created_at=_now(),
        experiment_manifest_path=_relative(experiment_manifest_path, root),
        experiment_manifest_sha256=_sha(experiment_manifest_path.read_bytes()),
        sanity_selection_sha256=_sha(sanity_selection_path.read_bytes()),
        direction_set_path=_relative(direction_set_path, root),
        direction_set_sha256=_sha(direction_set_path.read_bytes()),
        resolved_direction_artifacts=directions.artifacts,
        selected_strength_multiplier=selection.selected_strength_multiplier,
        samples_per_condition=config.thresholds.full_samples_per_condition,
        sandbox=experiment.sandbox,
        jobs=tuple(jobs),
        hook_by_direction=hook_by_direction,
        paired_seed_by_sample_index=paired_seeds,
    )
    _write_model(run_directory / "manifest.json", manifest)
    return manifest


def evaluate_stage4_full_run(
    manifest_path: Path,
    repository_root: Path,
    backend: SandboxBackend,
) -> int:
    manifest = _load(Stage4FullRunManifest, manifest_path)
    if backend.config != manifest.sandbox:
        raise Stage4Error("sandbox backend differs from the frozen Stage 4 manifest")
    experiment = _load(
        Stage4ExperimentManifest, repository_root.resolve() / manifest.experiment_manifest_path
    )
    run_directory = manifest_path.resolve().parent
    root = repository_root.resolve()
    manifest_sha = _sha(manifest_path.read_bytes())
    evaluated = 0
    for job in manifest.jobs:
        output = run_directory / f"jobs/{job.job_id}/evaluation.json"
        if output.exists():
            continue
        result_path = run_directory / job.result_path
        if not result_path.exists():
            continue
        result = _load(Stage4GenerationRecord, result_path)
        candidate = run_directory / job.candidate_path
        evaluation = None
        if result.status is GenerationStatus.GENERATED and candidate.exists():
            if _sha(candidate.read_bytes()) != result.candidate_sha256:
                raise Stage4Error(f"candidate hash mismatch: {job.job_id}")
            task = load_task(root / _task_path_for(experiment, root, job.task_id))
            evaluation = EvaluationHarness(root, backend).evaluate(task, candidate, task.tests)
            evaluated += 1
        artifact = Stage4EvaluationArtifact(
            job_id=job.job_id,
            manifest_sha256=manifest_sha,
            result_sha256=_sha(result_path.read_bytes()),
            candidate_sha256=result.candidate_sha256,
            evaluation=evaluation,
        )
        _write_model(output, artifact)
    return evaluated


def build_stage4_report(manifest_path: Path, repository_root: Path, output: Path) -> Stage4Report:
    manifest = _load(Stage4FullRunManifest, manifest_path)
    experiment = _load(
        Stage4ExperimentManifest, repository_root.resolve() / manifest.experiment_manifest_path
    )
    directory = manifest_path.resolve().parent
    grouped: dict[tuple[DirectionKind | None, PolicyValue | None], list[dict[str, bool]]] = (
        defaultdict(list)
    )
    complete = True
    evaluated_jobs = 0
    functional_both = 0
    manifest_sha = _sha(manifest_path.read_bytes())
    for job in manifest.jobs:
        path = directory / f"jobs/{job.job_id}/evaluation.json"
        if not path.exists():
            complete = False
            continue
        artifact = _load(Stage4EvaluationArtifact, path)
        result_path = directory / job.result_path
        if (
            artifact.job_id != job.job_id
            or artifact.manifest_sha256 != manifest_sha
            or not result_path.is_file()
            or artifact.result_sha256 != _sha(result_path.read_bytes())
        ):
            raise Stage4Error(f"evaluation provenance mismatch: {job.job_id}")
        if artifact.evaluation is None:
            complete = False
            continue
        generation = _load(Stage4GenerationRecord, result_path)
        if generation.candidate_sha256 != artifact.candidate_sha256:
            raise Stage4Error(f"evaluation candidate mismatch: {job.job_id}")
        if job.direction_kind is not None:
            hook = manifest.hook_by_direction[job.direction_kind]
            if (
                generation.hook != hook
                or generation.observed_end_plan_token_index != hook.token_index
                or generation.intervention_phase != "prompt_prefill"
                or generation.downstream_layers_receiving_edit
                != hook.downstream_layers_receiving_edit
                or generation.zero_strength_logits_identical is not True
            ):
                raise Stage4Error(f"intervention telemetry is incomplete: {job.job_id}")
        outcome_flags = _outcomes(artifact.evaluation)
        grouped[(job.direction_kind, job.target_policy)].append(outcome_flags)
        evaluated_jobs += 1
        functional_both += int(
            outcome_flags["functional"] and outcome_flags["A"] and outcome_flags["B"]
        )
    outcomes = tuple(
        _condition_outcome(kind, policy, rows)
        for (kind, policy), rows in sorted(grouped.items(), key=lambda item: str(item[0]))
    )
    lookup = {(row.direction_kind, row.target_policy): row for row in outcomes}
    unpatched = lookup.get((None, None))
    target_a = lookup.get((DirectionKind.POLICY_ORIENTATION, PolicyValue.A))
    target_b = lookup.get((DirectionKind.POLICY_ORIENTATION, PolicyValue.B))
    # A and B effects are opposite signed movements of the same A-minus-B behavioral contrast.
    # This is stricter than showing two unrelated target-rate increases.
    base_contrast = None if unpatched is None else _policy_contrast(unpatched)
    a_shift = (
        None
        if base_contrast is None or target_a is None
        else _policy_contrast(target_a) - base_contrast
    )
    b_shift = (
        None
        if base_contrast is None or target_b is None
        else base_contrast - _policy_contrast(target_b)
    )
    control_shifts = []
    if unpatched is not None:
        assert base_contrast is not None
        for outcome in outcomes:
            if outcome.direction_kind not in MATCHED_NULL_CONTROLS:
                continue
            observed_contrast = _policy_contrast(outcome)
            shift = (
                observed_contrast - base_contrast
                if outcome.target_policy is PolicyValue.A
                else base_contrast - observed_contrast
            )
            control_shifts.append(shift)
    strongest = max(control_shifts, default=None)
    bidirectional = a_shift is not None and b_shift is not None and a_shift > 0 and b_shift > 0
    target_min = min(a_shift, b_shift) if a_shift is not None and b_shift is not None else None
    exceeds = target_min is not None and (strongest is None or target_min > strongest)
    lost_a = (
        None
        if unpatched is None or target_a is None
        else max(0, unpatched.functional_count - target_a.functional_count)
    )
    lost_b = (
        None
        if unpatched is None or target_b is None
        else max(0, unpatched.functional_count - target_b.functional_count)
    )
    max_lost = load_stage4_config(
        repository_root.resolve() / experiment.config_path
    ).thresholds.target_functionality_max_lost_outputs
    functionality_ok = lost_a is not None and lost_b is not None and max(lost_a, lost_b) <= max_lost
    expected_jobs = len(manifest.jobs)
    is_complete = complete and evaluated_jobs == expected_jobs and len(outcomes) == 17
    invalid_tests = functional_both > 0
    set2_verified = all(
        candidate.paraphrase_set == "set2"
        for recipient in experiment.recipients
        for candidate in (recipient.explicit_a, recipient.explicit_b, recipient.omitted)
    )
    report = Stage4Report(
        created_at=_now(),
        run_id=manifest.run_id,
        full_run_manifest_sha256=_sha(manifest_path.read_bytes()),
        complete=is_complete,
        status=(
            "invalid_task_or_tests"
            if invalid_tests
            else "complete"
            if is_complete
            else "incomplete"
        ),
        evaluated_jobs=evaluated_jobs,
        expected_jobs=expected_jobs,
        heldout_tasks=tuple(
            sorted({row.task_id for row in experiment.recipients if row.split is SplitName.TEST})
        ),
        outcomes=outcomes,
        a_injection_shift=a_shift,
        b_injection_shift=b_shift,
        strongest_matched_control_shift=strongest,
        matched_null_control_kinds=tuple(sorted(MATCHED_NULL_CONTROLS)),
        diagnostic_kinds_excluded_from_success=(
            DirectionKind.UNRELATED_TASK_VALUE,
            DirectionKind.PREREGISTERED_EARLY_LAYER,
            DirectionKind.FULL_VECTOR_SAME_TASK,
        ),
        bidirectional=bidirectional,
        exceeds_every_matched_control=exceeds,
        target_a_functional_outputs_lost=lost_a,
        target_b_functional_outputs_lost=lost_b,
        functionality_within_one_paired_sample=functionality_ok,
        survives_paraphrase_set2=set2_verified,
        functional_outputs_passing_both_suites=functional_both,
        causal_success=(
            is_complete
            and not invalid_tests
            and bidirectional
            and exceeds
            and functionality_ok
            and set2_verified
        ),
    )
    _write_model(output, report)
    return report


def _require_stage3_authorization(
    config: Stage4Config, root: Path, dataset: Stage3Dataset, report: Stage3Report
) -> None:
    if _sha((root / config.stage3_dataset_path).read_bytes()) != report.dataset_sha256:
        raise Stage4Error("Stage 3 report references another activation dataset")
    required = report.stage4_authorization_requirements
    exact = (
        report.renderer_ingestion_decodability_scope
        == "heldout_supported_omitted_or_blurred_plans"
        and required.get("renderer_ingestion_decodable") is True
        and required.get("renderer_ingestion_transfers_to_paraphrase_set2") is True
        and required.get("renderer_ingestion_task_directions_align") is True
    )
    if not report.causal_evaluation_authorized or not exact or not dataset.complete:
        raise Stage4Error(
            "Stage 4 requires renderer-ingestion decodability, set-2 transfer, aligned "
            "renderer-ingestion task directions, and a complete dataset"
        )


def _validate_recipient_audit(
    audit_path: Path, dataset_path: Path, report_path: Path, root: Path
) -> tuple[SelectedRecipient, ...]:
    audit = _load(Stage4RecipientAudit, audit_path)
    if audit.stage3_dataset_sha256 != _sha(dataset_path.read_bytes()):
        raise Stage4Error("recipient audit references another Stage 3 dataset")
    if audit.stage3_report_sha256 != _sha(report_path.read_bytes()):
        raise Stage4Error("recipient audit references another Stage 3 report")
    if (
        not audit.reviewer
        or not audit.completed_at
        or not all(row.complete for row in audit.selections)
    ):
        raise Stage4Error("recipient audit is incomplete")
    dataset = load_stage3_dataset(dataset_path)
    plans = load_plan_texts(dataset, root)
    expected_candidates = {
        row.job_id: _recipient_candidate(row, plans[row.job_id])
        for row in dataset.rows
        if row.plan_sha256 is not None
        and row.policy_visibility is not None
        and row.plan_tokens is not None
        and row.split in (SplitName.DEV, SplitName.TEST)
    }
    candidates = {row.job_id: row for row in audit.candidates}
    if candidates != expected_candidates:
        raise Stage4Error("recipient audit candidate rows differ from the frozen Stage 3 dataset")
    selected: list[SelectedRecipient] = []
    for row in audit.selections:
        assert row.explicit_a_job_id and row.explicit_b_job_id and row.omitted_recipient_job_id
        identifiers = (
            row.explicit_a_job_id,
            row.explicit_b_job_id,
            row.omitted_recipient_job_id,
        )
        if len(set(identifiers)) != 3 or any(item not in candidates for item in identifiers):
            raise Stage4Error("recipient audit contains a missing or repeated candidate id")
        a, b, omitted = (candidates[item] for item in identifiers)
        if not _is_explicit(a, PolicyValue.A) or not _is_explicit(b, PolicyValue.B):
            raise Stage4Error("recipient audit selected an invalid explicit source")
        if not _is_omitted(omitted):
            raise Stage4Error("recipient audit selected a non-omitted or contradictory recipient")
        if {a.task_id, b.task_id, omitted.task_id} != {row.task_id}:
            raise Stage4Error("source and recipient plans must use the same task")
        booleans = (
            row.audited_without_generated_code_or_test_outcomes,
            row.same_surface_request,
            row.omitted_plan_functionally_meaningful,
            row.omitted_plan_neutral_between_a_and_b,
            row.format_length_and_nontarget_information_matched_where_possible,
        )
        if not all(value is True for value in booleans):
            raise Stage4Error("recipient audit did not pass every design requirement")
        selected.append(
            SelectedRecipient(
                split=row.split,
                task_id=row.task_id,
                explicit_a=a,
                explicit_b=b,
                omitted=omitted,
            )
        )
    return tuple(selected)


def _direction_artifacts(
    root: Path,
    selection: Stage3Selection,
    selection_path: Path,
    selected_layer: int,
    early_layer: int,
    run_directory: Path,
) -> list[DirectionArtifact]:
    """Freeze layer-matched controls and declare the controls derived on the GPU PC."""
    state = BoundaryState.RENDERER_INGESTION.value
    mapping = {
        DirectionKind.PARAPHRASE_IDENTITY: f"{state}:L{selected_layer}:paraphrase_set_identity",
        DirectionKind.LEXICAL_FRAMING: (
            f"{state}:L{selected_layer}:from_prohibition_to_permission"
        ),
    }
    artifacts: list[DirectionArtifact] = []
    for kind, key in mapping.items():
        relative = selection.control_directions.get(key)
        if relative is None:
            raise Stage4Error(f"Stage 3 selection lacks layer-matched {kind.value}")
        absolute = root / relative
        artifacts.append(
            DirectionArtifact(
                kind=kind,
                role=direction_role(kind),
                layer=selected_layer,
                path=relative,
                sha256=_sha(absolute.read_bytes()),
                derivation=key,
            )
        )

    target_path = (
        selection_path.parent / "directions" / (f"renderer_ingestion__L{selected_layer:02d}.npy")
    )
    random_path = (
        run_directory
        / "directions"
        / (f"renderer_ingestion__L{selected_layer:02d}__random_orthogonal.npy")
    )
    random_dot = _save_random_orthogonal(target_path, random_path, 20260912)
    if random_dot > 1e-5:
        raise Stage4Error("failed to construct an orthogonal random control")
    artifacts.append(
        DirectionArtifact(
            kind=DirectionKind.RANDOM_ORTHOGONAL,
            role=direction_role(DirectionKind.RANDOM_ORTHOGONAL),
            layer=selected_layer,
            path=_relative(random_path, root),
            sha256=_sha(random_path.read_bytes()),
            derivation="seeded Gaussian vector projected off the policy-orientation direction",
        )
    )

    fit = _load(Stage3ProbeFit, selection_path.parent / "probes-dev.json")
    early_cell = next(
        (
            cell
            for state_fit in fit.states
            if state_fit.state is BoundaryState.RENDERER_INGESTION
            for cell in state_fit.cells
            if cell.layer == early_layer
        ),
        None,
    )
    if early_cell is None:
        raise Stage4Error(f"preregistered early layer {early_layer} was not captured")
    early_path = (
        selection_path.parent / "directions" / (f"renderer_ingestion__L{early_layer:02d}.npy")
    )
    if _sha(early_path.read_bytes()) != early_cell.direction.direction_sha256:
        raise Stage4Error("preregistered early-layer direction hash mismatch")
    artifacts.extend(
        (
            DirectionArtifact(
                kind=DirectionKind.UNRELATED_SECURITY_FACT,
                role=direction_role(DirectionKind.UNRELATED_SECURITY_FACT),
                layer=selected_layer,
                path=None,
                sha256=None,
                derivation="paired renderer-ingestion capture of frozen authentication facts",
            ),
            DirectionArtifact(
                kind=DirectionKind.UNRELATED_TASK_VALUE,
                role=direction_role(DirectionKind.UNRELATED_TASK_VALUE),
                layer=selected_layer,
                path=_relative(target_path, root),
                sha256=_sha(target_path.read_bytes()),
                derivation="target direction with scalar value from audited development task",
                centroids=selection.centroids[BoundaryState.RENDERER_INGESTION],
            ),
            DirectionArtifact(
                kind=DirectionKind.PREREGISTERED_EARLY_LAYER,
                role=direction_role(DirectionKind.PREREGISTERED_EARLY_LAYER),
                layer=early_layer,
                path=_relative(early_path, root),
                sha256=_sha(early_path.read_bytes()),
                derivation="task-balanced set-1 policy direction at preregistered early layer",
                centroids=(
                    early_cell.direction.centroid_a,
                    early_cell.direction.centroid_b,
                ),
            ),
            DirectionArtifact(
                kind=DirectionKind.FULL_VECTOR_SAME_TASK,
                role=direction_role(DirectionKind.FULL_VECTOR_SAME_TASK),
                layer=selected_layer,
                path=None,
                sha256=None,
                derivation="held-out explicit-B minus explicit-A source activation",
            ),
        )
    )
    return artifacts


def _recipient_candidate(row: Stage3DatasetRow, plan: str) -> RecipientCandidate:
    assert row.plan_sha256 is not None and row.plan_tokens is not None
    assert row.policy_visibility is not None
    return RecipientCandidate(
        job_id=row.job_id,
        task_id=row.task_id,
        split=row.split,
        assigned_policy=row.assigned_policy,
        paraphrase_set=row.paraphrase_set.value,
        plan_format=row.plan_format.value,
        concision=row.concision.value,
        policy_visibility=row.policy_visibility,
        plan_tokens=row.plan_tokens,
        plan_sha256=row.plan_sha256,
        plan=plan,
    )


def _is_explicit(row: RecipientCandidate, policy: PolicyValue) -> bool:
    return (
        row.assigned_policy is policy
        and row.paraphrase_set == "set2"
        and row.concision == "full"
        and row.policy_visibility is PolicyVisibility.PRESERVED
    )


def _is_omitted(row: RecipientCandidate) -> bool:
    return (
        row.paraphrase_set == "set2"
        and row.concision in ("concise", "minimal")
        and row.policy_visibility in (PolicyVisibility.OMITTED, PolicyVisibility.AMBIGUOUS)
    )


def _task_path_for(experiment: Stage4ExperimentManifest, root: Path, task_id: str) -> str:
    stage2_path = root / experiment.stage2_config_path
    if _sha(stage2_path.read_bytes()) != experiment.stage2_config_sha256:
        raise Stage4Error("Stage 2 config changed after the Stage 4 experiment was frozen")
    stage2 = load_stage2_config(stage2_path)
    for path in stage2.task_paths:
        if load_task(root / path).id == task_id:
            return path
    raise Stage4Error(f"unknown Stage 4 task: {task_id}")


def _outcomes(evaluation: EvaluationResult) -> dict[str, bool]:
    return {
        "functional": _suite_passed(evaluation, TestSuiteKind.FUNCTIONALITY),
        "A": _suite_passed(evaluation, TestSuiteKind.POLICY_A),
        "B": _suite_passed(evaluation, TestSuiteKind.POLICY_B),
    }


def _suite_passed(evaluation: EvaluationResult, kind: TestSuiteKind) -> bool:
    result = evaluation.suites.get(kind)
    return result is not None and result.status.value == "passed"


def _condition_outcome(
    kind: DirectionKind | None, policy: PolicyValue | None, rows: list[dict[str, bool]]
) -> ConditionOutcome:
    denominator = len(rows)
    return ConditionOutcome(
        direction_kind=kind,
        target_policy=policy,
        samples=denominator,
        functional_count=sum(row["functional"] for row in rows),
        functional_rate=sum(row["functional"] for row in rows) / denominator,
        policy_a_and_functional_rate=sum(row["functional"] and row["A"] for row in rows)
        / denominator,
        policy_b_and_functional_rate=sum(row["functional"] and row["B"] for row in rows)
        / denominator,
    )


def _policy_contrast(outcome: ConditionOutcome) -> float:
    return outcome.policy_a_and_functional_rate - outcome.policy_b_and_functional_rate


def _seed(run_id: str, job_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{run_id}:{job_id}".encode()).digest()[:4], "big")


def _save_random_orthogonal(target_path: Path, output: Path, seed: int) -> float:
    import numpy as np

    target = np.load(target_path).astype(np.float64)
    target /= np.linalg.norm(target)
    random = np.random.default_rng(seed).standard_normal(target.shape).astype(np.float64)
    random -= float(random @ target) * target
    random /= np.linalg.norm(random)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        np.save(handle, random.astype(np.float32))
    return abs(float(random @ target))


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise Stage4Error(f"artifact must live inside the repository: {path}")
    return resolved.relative_to(root).as_posix()


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise Stage4Error(f"cannot load {model.__name__} from {path}: {error}") from error


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_model(path: Path, model: StrictModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise Stage4Error(f"refusing to overwrite {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(model.model_dump_json(indent=2) + "\n")
