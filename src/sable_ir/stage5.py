"""Hash-bound downstream monitorability, ambiguity, and evaluation dataset assembly."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, TypeVar

from pydantic import Field, ValidationError, model_validator

from sable_ir.config import load_task
from sable_ir.harness import EvaluationResult, RunStatus
from sable_ir.schema import PolicyValue, StrictModel, TaskSpec, TestSuiteKind
from sable_ir.scoring import RawOutcome
from sable_ir.stage1 import RenderManifest, RenderRecord
from sable_ir.stage1_addendum import (
    Stage1CompletionReportV2,
    Stage1RobustnessAddendum,
)
from sable_ir.stage1_analysis import (
    BehavioralMetrics,
    BehavioralRow,
    ClauseSelection,
    LengthReport,
    PlanAudit,
    PolicyVisibility,
)
from sable_ir.stage1_controls import SurfaceBaselineReport
from sable_ir.stage1_report import Stage1Recommendation, Stage1Report
from sable_ir.stage2 import SplitName, Stage2Config, load_stage2_config
from sable_ir.stage2_local import (
    CandidateResult,
    EvalKind,
    RenderRow,
    Stage2EvalManifest,
    Stage2EvalReport,
    Stage2PlanAudit,
    load_eval_manifest,
)
from sable_ir.stage3 import (
    ActivationRenderJob,
    PlanCaptureResult,
    Stage3Dataset,
    Stage3EvaluationArtifact,
    Stage3PlanAudit,
    load_activation_manifest,
    load_stage3_dataset,
)
from sable_ir.stage3_analysis import Stage3Report
from sable_ir.stage4 import (
    Stage4EvaluationArtifact,
    Stage4ExperimentManifest,
    Stage4FullRunManifest,
    Stage4GenerationRecord,
    Stage4Report,
)

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelT = TypeVar("ModelT", bound=StrictModel)


class Stage5Error(RuntimeError):
    """Downstream analysis input or provenance is invalid."""


class SourceStage(StrEnum):
    STAGE1 = "stage1_hosted"
    STAGE2_FLOOR = "stage2_model_floor"
    STAGE2_TEST = "stage2_test_final"
    STAGE3 = "stage3_activation_dataset"
    STAGE4 = "stage4_unpatched"


class ModelScope(StrEnum):
    HOSTED_KIMI = "hosted_kimi_k2_6_behavior"
    LOCAL_QWEN = "local_qwen_renderer_behavior"


class Stage5Inputs(StrictModel):
    stage1_report_path: str
    stage1_primary_report_path: str
    stage1_robustness_addendum_path: str
    stage1_behavior_path: str
    stage1_length_path: str
    stage1_plan_audit_path: str
    stage1_render_manifest_path: str
    stage1_surface_report_path: str
    stage2_floor_manifest_path: str
    stage2_floor_report_path: str
    stage2_test_manifest_path: str
    stage2_test_report_path: str
    stage2_test_plan_audit_path: str
    stage3_dataset_path: str
    stage3_plan_audit_path: str
    stage3_report_path: str
    stage4_full_manifest_path: str
    stage4_report_path: str


class Stage5AnalysisConfig(StrictModel):
    ambiguity_min_functional_classifiable: Literal[8] = 8
    bootstrap_replicates: int = Field(ge=1000)
    bootstrap_seed: int = Field(ge=0)
    top_k: tuple[int, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_top_k(self) -> Stage5AnalysisConfig:
        if tuple(sorted(set(self.top_k))) != self.top_k or any(k < 1 for k in self.top_k):
            raise ValueError("top_k must be unique, positive, and increasing")
        return self


class Stage5Config(StrictModel):
    schema_version: Literal[1] = 1
    artifacts_dir: str
    stage2_config_path: str
    collision_rubric_path: str
    inputs: Stage5Inputs
    analysis: Stage5AnalysisConfig

    @model_validator(mode="after")
    def validate_paths(self) -> Stage5Config:
        values = [
            self.artifacts_dir,
            self.stage2_config_path,
            self.collision_rubric_path,
            *self.inputs.model_dump().values(),
        ]
        for value in values:
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "\\" in value:
                raise ValueError("Stage 5 paths must be repository-relative POSIX paths")
        return self


class Stage5ConfigSummary(StrictModel):
    valid: Literal[True] = True
    analysis_only: Literal[True] = True
    configured_inputs: int
    tasks: int
    train_tasks: int
    dev_tasks: int
    test_tasks: int
    ambiguity_support_floor: Literal[8] = 8
    bootstrap_replicates: int


class ArtifactBinding(StrictModel):
    label: str
    path: str
    sha256: Sha256


class Stage5InputManifest(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    created_at: str
    config_path: str
    config_sha256: Sha256
    analysis_only: Literal[True] = True
    all_prior_stages_complete: Literal[True] = True
    hosted_and_local_results_separate: Literal[True] = True
    base_tasks_are_independent_clusters: Literal[True] = True
    artifacts: tuple[ArtifactBinding, ...]
    task_splits: dict[SplitName, tuple[str, ...]]


class SampleOutcome(StrictModel):
    job_id: str
    sample_index: int
    generation_status: str
    compilation: RawOutcome
    functionality: RawOutcome
    policy_a: RawOutcome
    policy_b: RawOutcome
    original_security: RawOutcome
    candidate_path: str | None = None
    candidate_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def validate_candidate(self) -> SampleOutcome:
        if (self.candidate_path is None) != (self.candidate_sha256 is None):
            raise ValueError("candidate path and hash must appear together")
        return self


class PlanObservation(StrictModel):
    source: SourceStage
    model_scope: ModelScope
    run_id: str
    task_id: str
    family: str
    split: SplitName
    plan_job_id: str
    plan_sha256: Sha256
    assigned_policy: PolicyValue
    plan_format: str
    concision: str
    plan_tokens: int = Field(gt=0)
    content_tokens_without_fixed_labels: int | None = Field(default=None, gt=0)
    document_tokens: int = Field(gt=0)
    clause_selection: ClauseSelection | None
    policy_visibility: PolicyVisibility | None
    visible_policy_retained: bool | None
    irrelevant_clause_ids_included: tuple[str, ...] | None
    applicable_clause_ids: tuple[str, ...] | None
    selected_clause_ids: tuple[str, ...] | None
    audit_confident: bool | None
    natural_sampling: Literal[True] = True
    samples: tuple[SampleOutcome, ...]

    @model_validator(mode="after")
    def validate_samples(self) -> PlanObservation:
        if not self.samples or len({row.job_id for row in self.samples}) != len(self.samples):
            raise ValueError("each plan observation needs unique renderer samples")
        return self


class BaselineCell(StrictModel):
    source: SourceStage
    model_scope: ModelScope
    task_id: str
    policy: PolicyValue
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)


class CostDiagnostic(StrictModel):
    source: SourceStage
    model_scope: ModelScope
    scope: str
    planner_output_tokens: int | None = Field(default=None, ge=0)
    planner_reasoning_tokens: int | None = Field(default=None, ge=0)
    renderer_output_tokens: int | None = Field(default=None, ge=0)
    total_generated_tokens: int | None = Field(default=None, ge=0)
    planner_latency_seconds: float | None = Field(default=None, ge=0)
    renderer_latency_seconds: float | None = Field(default=None, ge=0)


class Stage5ObservationDataset(StrictModel):
    schema_version: Literal[1] = 1
    created_at: str
    input_manifest_sha256: Sha256
    prior_report_sha256: dict[str, Sha256]
    complete: Literal[True] = True
    rows: tuple[PlanObservation, ...]
    surface_baselines: tuple[BaselineCell, ...]
    cost_diagnostics: tuple[CostDiagnostic, ...]


def load_stage5_config(path: Path) -> Stage5Config:
    try:
        return Stage5Config.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise Stage5Error(f"cannot load Stage 5 config: {error}") from error


def validate_stage5_config(config_path: Path, repository_root: Path) -> Stage5ConfigSummary:
    config = load_stage5_config(config_path)
    root = repository_root.resolve()
    stage2 = load_stage2_config(root / config.stage2_config_path)
    split = _task_splits(stage2)
    return Stage5ConfigSummary(
        configured_inputs=len(Stage5Inputs.model_fields) + 2,
        tasks=sum(len(tasks) for tasks in split.values()),
        train_tasks=len(split[SplitName.TRAIN]),
        dev_tasks=len(split[SplitName.DEV]),
        test_tasks=len(split[SplitName.TEST]),
        bootstrap_replicates=config.analysis.bootstrap_replicates,
    )


def prepare_stage5_inputs(
    config_path: Path, repository_root: Path, output: Path, run_id: str
) -> Stage5InputManifest:
    """Freeze complete Stage 1-4 inputs; this performs no generation or evaluation."""
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", run_id):
        raise Stage5Error("run IDs must be 1-64 safe filename characters")
    config = load_stage5_config(config_path)
    root = repository_root.resolve()
    paths = _input_paths(config, root)
    missing = [label for label, path in paths.items() if not path.is_file()]
    if missing:
        raise Stage5Error(f"prior-stage artifacts are missing: {', '.join(missing)}")
    loaded = _load_prior_inputs(paths)
    _validate_prior_inputs(paths, loaded, root)
    bindings = tuple(
        ArtifactBinding(label=label, path=_relative(path, root), sha256=_sha(path.read_bytes()))
        for label, path in sorted(paths.items())
    )
    stage2 = load_stage2_config(root / config.stage2_config_path)
    manifest = Stage5InputManifest(
        run_id=run_id,
        created_at=_now(),
        config_path=_relative(config_path, root),
        config_sha256=_sha(config_path.read_bytes()),
        artifacts=bindings,
        task_splits=_task_splits(stage2),
    )
    _write_model(output, manifest)
    return manifest


def assemble_stage5_observations(
    manifest_path: Path, repository_root: Path, output: Path
) -> Stage5ObservationDataset:
    manifest = _load(Stage5InputManifest, manifest_path)
    root = repository_root.resolve()
    config_path = root / manifest.config_path
    if _sha(config_path.read_bytes()) != manifest.config_sha256:
        raise Stage5Error("Stage 5 config changed after input freeze")
    config = load_stage5_config(config_path)
    paths = _bound_paths(manifest, root)
    loaded = _load_prior_inputs(paths)
    _validate_prior_inputs(paths, loaded, root)
    stage2 = load_stage2_config(root / config.stage2_config_path)
    task_specs = {spec.id: spec for spec in (load_task(root / path) for path in stage2.task_paths)}
    split_lookup = {task: split for split, tasks in manifest.task_splits.items() for task in tasks}
    stage2_test_audit = loaded["stage2_test_plan_audit"]
    assert isinstance(stage2_test_audit, Stage2PlanAudit)
    rows: list[PlanObservation] = []
    rows.extend(_stage1_rows(paths, loaded, task_specs, split_lookup, root))
    rows.extend(
        _stage2_rows(
            SourceStage.STAGE2_FLOOR,
            paths["stage2_floor_manifest"],
            loaded["stage2_floor_manifest"],
            loaded["stage2_floor_report"],
            task_specs,
            root,
        )
    )
    rows.extend(
        _stage2_rows(
            SourceStage.STAGE2_TEST,
            paths["stage2_test_manifest"],
            loaded["stage2_test_manifest"],
            loaded["stage2_test_report"],
            task_specs,
            root,
            stage2_test_audit,
        )
    )
    rows.extend(_stage3_rows(paths, loaded, root))
    rows.extend(_stage4_rows(paths, loaded, task_specs, root))
    baselines = [*_stage1_baselines(loaded), *_stage2_baselines(loaded["stage2_floor_report"])]
    dataset = Stage5ObservationDataset(
        created_at=_now(),
        input_manifest_sha256=_sha(manifest_path.read_bytes()),
        prior_report_sha256={
            "stage1": _sha(paths["stage1_report"].read_bytes()),
            "stage2_floor": _sha(paths["stage2_floor_report"].read_bytes()),
            "stage2_test": _sha(paths["stage2_test_report"].read_bytes()),
            "stage3": _sha(paths["stage3_report"].read_bytes()),
            "stage4": _sha(paths["stage4_report"].read_bytes()),
        },
        rows=tuple(sorted(rows, key=lambda row: (row.source, row.plan_job_id))),
        surface_baselines=tuple(
            sorted(baselines, key=lambda row: (row.source, row.task_id, row.policy))
        ),
        cost_diagnostics=_cost_diagnostics(paths, loaded, root),
    )
    _write_model(output, dataset)
    return dataset


def _input_paths(config: Stage5Config, root: Path) -> dict[str, Path]:
    paths = {
        name.removesuffix("_path"): root / value
        for name, value in config.inputs.model_dump().items()
    }
    paths["stage2_config"] = root / config.stage2_config_path
    paths["collision_rubric"] = root / config.collision_rubric_path
    return paths


def _bound_paths(manifest: Stage5InputManifest, root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for binding in manifest.artifacts:
        path = (root / binding.path).resolve()
        if not path.is_relative_to(root) or _sha(path.read_bytes()) != binding.sha256:
            raise Stage5Error(f"bound input changed or escaped repository: {binding.label}")
        paths[binding.label] = path
    return paths


def _load_prior_inputs(paths: dict[str, Path]) -> dict[str, StrictModel]:
    return {
        "stage1_report": _load(Stage1CompletionReportV2, paths["stage1_report"]),
        "stage1_primary_report": _load(Stage1Report, paths["stage1_primary_report"]),
        "stage1_robustness_addendum": _load(
            Stage1RobustnessAddendum, paths["stage1_robustness_addendum"]
        ),
        "stage1_behavior": _load(BehavioralMetrics, paths["stage1_behavior"]),
        "stage1_length": _load(LengthReport, paths["stage1_length"]),
        "stage1_plan_audit": _load(PlanAudit, paths["stage1_plan_audit"]),
        "stage1_render_manifest": _load(RenderManifest, paths["stage1_render_manifest"]),
        "stage1_surface_report": _load(SurfaceBaselineReport, paths["stage1_surface_report"]),
        "stage2_floor_manifest": load_eval_manifest(paths["stage2_floor_manifest"]),
        "stage2_floor_report": _load(Stage2EvalReport, paths["stage2_floor_report"]),
        "stage2_test_manifest": load_eval_manifest(paths["stage2_test_manifest"]),
        "stage2_test_report": _load(Stage2EvalReport, paths["stage2_test_report"]),
        "stage2_test_plan_audit": _load(Stage2PlanAudit, paths["stage2_test_plan_audit"]),
        "stage3_dataset": load_stage3_dataset(paths["stage3_dataset"]),
        "stage3_plan_audit": _load(Stage3PlanAudit, paths["stage3_plan_audit"]),
        "stage3_report": _load(Stage3Report, paths["stage3_report"]),
        "stage4_full_manifest": _load(Stage4FullRunManifest, paths["stage4_full_manifest"]),
        "stage4_report": _load(Stage4Report, paths["stage4_report"]),
    }


def _validate_prior_inputs(
    paths: dict[str, Path], loaded: dict[str, StrictModel], root: Path
) -> None:
    stage2_config_sha = _sha(paths["stage2_config"].read_bytes())
    stage2_config = load_stage2_config(paths["stage2_config"])
    configured_tasks = {
        _relative(root / task_path, root): _sha((root / task_path).read_bytes())
        for task_path in stage2_config.task_paths
    }
    s1 = loaded["stage1_report"]
    s1_primary = loaded["stage1_primary_report"]
    s1_addendum = loaded["stage1_robustness_addendum"]
    behavior = loaded["stage1_behavior"]
    lengths = loaded["stage1_length"]
    audit = loaded["stage1_plan_audit"]
    render_manifest = loaded["stage1_render_manifest"]
    surface = loaded["stage1_surface_report"]
    assert isinstance(s1, Stage1CompletionReportV2)
    assert isinstance(s1_primary, Stage1Report)
    assert isinstance(s1_addendum, Stage1RobustnessAddendum)
    assert isinstance(behavior, BehavioralMetrics)
    assert isinstance(lengths, LengthReport)
    assert isinstance(audit, PlanAudit)
    assert isinstance(render_manifest, RenderManifest)
    assert isinstance(surface, SurfaceBaselineReport)
    if s1.recommendation is not Stage1Recommendation.CONTINUE_TO_STAGE2:
        raise Stage5Error("Stage 1 is not a completed continue_to_stage2 result")
    primary_sha256 = _sha(paths["stage1_primary_report"].read_bytes())
    addendum_sha256 = _sha(paths["stage1_robustness_addendum"].read_bytes())
    if (
        s1.primary_stage1_report_sha256 != primary_sha256
        or s1.robustness_addendum_sha256 != addendum_sha256
        or s1.primary_report != s1_primary
        or s1.robustness_addendum != s1_addendum
        or s1_addendum.canonical_stage1_report_sha256 != primary_sha256
        or s1.primary_progression_gate_modified
        or s1.robustness_effect_size_stop_gate is not None
    ):
        raise Stage5Error("Stage 1 v2 does not bind the configured primary/addendum evidence")
    if s1_primary.recommendation is not Stage1Recommendation.CONTINUE_TO_STAGE2:
        raise Stage5Error("Stage 1 primary report is not an approved result")
    expected_s1 = {
        "natural_behavior_sha256": _sha(paths["stage1_behavior"].read_bytes()),
        "length_report_sha256": _sha(paths["stage1_length"].read_bytes()),
        "plan_audit_sha256": _sha(paths["stage1_plan_audit"].read_bytes()),
    }
    if any(getattr(s1_primary, field) != digest for field, digest in expected_s1.items()):
        raise Stage5Error("Stage 1 report does not bind the configured analysis artifacts")
    if behavior.render_manifest_sha256 != _sha(paths["stage1_render_manifest"].read_bytes()):
        raise Stage5Error("Stage 1 behavior references another natural render manifest")
    if behavior.surface_baseline_sha256 != _sha(paths["stage1_surface_report"].read_bytes()):
        raise Stage5Error("Stage 1 behavior references another surface baseline")
    if behavior.evaluated_rows != behavior.expected_rows or surface.evaluated != surface.expected:
        raise Stage5Error("Stage 1 behavioral inputs are incomplete")
    if not audit.reviewer or not audit.completed_at or not all(row.complete for row in audit.rows):
        raise Stage5Error("Stage 1 behavior-blinded plan audit is incomplete")
    stage1_tasks = {job.task_path: job.task_sha256 for job in render_manifest.jobs}
    if stage1_tasks != configured_tasks:
        raise Stage5Error("Stage 1 task hashes do not match the bound Stage 2 task set")

    for prefix, expected_kind in (
        ("stage2_floor", EvalKind.MODEL_FLOOR),
        ("stage2_test", EvalKind.TEST_FINAL),
    ):
        manifest = loaded[f"{prefix}_manifest"]
        report = loaded[f"{prefix}_report"]
        assert isinstance(manifest, Stage2EvalManifest)
        assert isinstance(report, Stage2EvalReport)
        if manifest.config_sha256 != stage2_config_sha:
            raise Stage5Error(f"{prefix} was prepared from another Stage 2 config")
        manifest_tasks = {row.task_path: row.task_sha256 for row in manifest.tasks}
        expected_tasks = {
            path: digest
            for path, digest in configured_tasks.items()
            if any(row.task_path == path for row in manifest.tasks)
        }
        if manifest_tasks != expected_tasks:
            raise Stage5Error(f"{prefix} task hashes do not match the bound task files")
        if report.eval_manifest_sha256 != _sha(paths[f"{prefix}_manifest"].read_bytes()):
            raise Stage5Error(f"{prefix} report references another manifest")
        if report.kind is not expected_kind or not report.complete:
            raise Stage5Error(f"{prefix} is incomplete or has the wrong evaluation kind")
        if report.invalid_task_or_tests:
            raise Stage5Error(f"{prefix} contains a functional output passing both A/B suites")
        if report.stage2_status != "valid_continuation":
            raise Stage5Error(f"{prefix} is not a valid Stage 1 continuation")
    test = loaded["stage2_test_report"]
    assert isinstance(test, Stage2EvalReport)
    if test.plan_audit_sha256 is None:
        raise Stage5Error("Stage 2 final-test monitorability requires its behavior-blinded audit")
    if test.plan_audit_sha256 != _sha(paths["stage2_test_plan_audit"].read_bytes()):
        raise Stage5Error("Stage 2 final report references another plan audit")
    test_audit = loaded["stage2_test_plan_audit"]
    assert isinstance(test_audit, Stage2PlanAudit)
    if not test_audit.complete:
        raise Stage5Error("Stage 2 final behavior-blinded plan audit is incomplete")

    dataset = loaded["stage3_dataset"]
    s3 = loaded["stage3_report"]
    assert isinstance(dataset, Stage3Dataset)
    assert isinstance(s3, Stage3Report)
    if not dataset.complete or s3.dataset_sha256 != _sha(paths["stage3_dataset"].read_bytes()):
        raise Stage5Error("Stage 3 dataset/report is incomplete or mismatched")
    stage3_audit = loaded["stage3_plan_audit"]
    assert isinstance(stage3_audit, Stage3PlanAudit)
    if not stage3_audit.complete or dataset.primary_audit_sha256 != _sha(
        paths["stage3_plan_audit"].read_bytes()
    ):
        raise Stage5Error("Stage 3 behavior-blinded plan audit is incomplete or mismatched")
    if s3.status.stage3_status != "valid_continuation":
        raise Stage5Error("Stage 3 does not have valid-continuation standing")

    full = loaded["stage4_full_manifest"]
    s4 = loaded["stage4_report"]
    assert isinstance(full, Stage4FullRunManifest)
    assert isinstance(s4, Stage4Report)
    if s4.full_run_manifest_sha256 != _sha(paths["stage4_full_manifest"].read_bytes()):
        raise Stage5Error("Stage 4 report references another full-run manifest")
    if not s4.complete or s4.status != "complete" or s4.evaluated_jobs != s4.expected_jobs:
        raise Stage5Error("Stage 4 is incomplete or invalid_task_or_tests")


def _stage1_rows(
    paths: dict[str, Path],
    loaded: dict[str, StrictModel],
    tasks: dict[str, TaskSpec],
    split_lookup: dict[str, SplitName],
    root: Path,
) -> list[PlanObservation]:
    behavior = loaded["stage1_behavior"]
    lengths = loaded["stage1_length"]
    audit = loaded["stage1_plan_audit"]
    manifest = loaded["stage1_render_manifest"]
    assert isinstance(behavior, BehavioralMetrics)
    assert isinstance(lengths, LengthReport)
    assert isinstance(audit, PlanAudit)
    assert isinstance(manifest, RenderManifest)
    by_length = {row.job_id: row for row in lengths.rows}
    by_audit = {row.job_id: row for row in audit.rows}
    jobs = {row.job_id: row for row in manifest.jobs}
    grouped: dict[str, list[BehavioralRow]] = defaultdict(list)
    for row in behavior.rows:
        grouped[row.source_plan_job_id].append(row)
    output: list[PlanObservation] = []
    directory = paths["stage1_render_manifest"].parent
    for plan_id, values in grouped.items():
        first = values[0]
        length = by_length[plan_id]
        audit_row = by_audit[plan_id]
        render_samples: list[SampleOutcome] = []
        for value in values:
            job = jobs[value.job_id]
            record = _load(RenderRecord, directory / job.result_path)
            candidate_path = None
            candidate_sha = None
            if record.candidate_path and record.candidate_sha256:
                candidate = (directory / record.candidate_path).resolve()
                _verify_candidate(candidate, record.candidate_sha256, root)
                candidate_path = _relative(candidate, root)
                candidate_sha = record.candidate_sha256
            render_samples.append(
                SampleOutcome(
                    job_id=value.job_id,
                    sample_index=value.render_sample_index,
                    generation_status=value.generation_status.value,
                    compilation=value.compilation,
                    functionality=value.functionality,
                    policy_a=value.policy_a,
                    policy_b=value.policy_b,
                    original_security=value.original_security,
                    candidate_path=candidate_path,
                    candidate_sha256=candidate_sha,
                )
            )
        spec = tasks[first.task_id]
        output.append(
            PlanObservation(
                source=SourceStage.STAGE1,
                model_scope=ModelScope.HOSTED_KIMI,
                run_id=manifest.run_id,
                task_id=first.task_id,
                family=spec.family.value,
                split=split_lookup[first.task_id],
                plan_job_id=plan_id,
                plan_sha256=jobs[values[0].job_id].plan_sha256,
                assigned_policy=first.assigned_policy,
                plan_format=first.plan_format.value,
                concision=first.nominal_concision,
                plan_tokens=length.plan_tokens,
                content_tokens_without_fixed_labels=(
                    length.secondary_content_tokens_without_labels_or_sentinel
                ),
                document_tokens=length.safety_document_tokens,
                clause_selection=audit_row.clause_selection,
                policy_visibility=audit_row.policy_visibility,
                visible_policy_retained=first.visible_policy_retained,
                irrelevant_clause_ids_included=audit_row.irrelevant_clause_ids_included,
                applicable_clause_ids=audit_row.applicable_clause_ids,
                selected_clause_ids=audit_row.selected_clause_ids,
                audit_confident=(
                    None
                    if audit_row.confidence is None
                    else audit_row.confidence.value == "confident"
                ),
                samples=tuple(sorted(render_samples, key=lambda row: row.sample_index)),
            )
        )
    return output


def _stage2_rows(
    source: SourceStage,
    manifest_path: Path,
    manifest_model: StrictModel,
    report_model: StrictModel,
    tasks: dict[str, TaskSpec],
    root: Path,
    plan_audit: Stage2PlanAudit | None = None,
) -> list[PlanObservation]:
    assert isinstance(manifest_model, Stage2EvalManifest)
    assert isinstance(report_model, Stage2EvalReport)
    directory = manifest_path.parent
    plan_jobs = {row.job_id: row for row in manifest_model.plan_jobs}
    grouped: dict[str, list[RenderRow]] = defaultdict(list)
    for row in report_model.rows:
        grouped[row.plan_job_id].append(row)
    output: list[PlanObservation] = []
    audit_rows = {} if plan_audit is None else {row.job_id: row for row in plan_audit.rows}
    for plan_id, values in grouped.items():
        first = values[0]
        plan_job = plan_jobs[plan_id]
        plan_result = _json(directory / plan_job.result_path)
        plan_sha = plan_result.get("plan_sha256")
        if not isinstance(plan_sha, str):
            raise Stage5Error(f"Stage 2 plan lacks a hash: {plan_id}")
        samples: list[SampleOutcome] = []
        for value in values:
            result_path = directory / f"jobs/{value.job_id}/result.json"
            candidate = _load(CandidateResult, result_path)
            candidate_path = None
            candidate_sha = None
            if candidate.candidate_path and candidate.candidate_sha256:
                path = (directory / candidate.candidate_path).resolve()
                _verify_candidate(path, candidate.candidate_sha256, root)
                candidate_path = _relative(path, root)
                candidate_sha = candidate.candidate_sha256
            samples.append(
                SampleOutcome(
                    job_id=value.job_id,
                    sample_index=value.render_index,
                    generation_status=value.render_status.value,
                    compilation=value.compilation,
                    functionality=value.functionality,
                    policy_a=value.policy_a,
                    policy_b=value.policy_b,
                    original_security=value.original_security,
                    candidate_path=candidate_path,
                    candidate_sha256=candidate_sha,
                )
            )
        spec = tasks[first.task_id]
        audit_row = audit_rows.get(plan_id)
        output.append(
            PlanObservation(
                source=source,
                model_scope=ModelScope.LOCAL_QWEN,
                run_id=manifest_model.run_id,
                task_id=first.task_id,
                family=spec.family.value,
                split=first.split,
                plan_job_id=plan_id,
                plan_sha256=plan_sha,
                assigned_policy=first.assigned_policy,
                plan_format=first.plan_format.value,
                concision=first.concision.value,
                plan_tokens=first.plan_tokens or 1,
                document_tokens=first.document_tokens or 1,
                clause_selection=first.clause_selection,
                policy_visibility=(
                    PolicyVisibility.PRESERVED
                    if first.visible_policy_retained is True
                    else PolicyVisibility.OMITTED
                    if first.visible_policy_retained is False
                    else None
                ),
                visible_policy_retained=first.visible_policy_retained,
                irrelevant_clause_ids_included=None,
                applicable_clause_ids=(
                    None if audit_row is None else audit_row.applicable_clause_ids
                ),
                selected_clause_ids=None if audit_row is None else audit_row.selected_clause_ids,
                audit_confident=None,
                samples=tuple(sorted(samples, key=lambda row: row.sample_index)),
            )
        )
    return output


def _stage3_rows(
    paths: dict[str, Path], loaded: dict[str, StrictModel], root: Path
) -> list[PlanObservation]:
    dataset = loaded["stage3_dataset"]
    audit = loaded["stage3_plan_audit"]
    assert isinstance(dataset, Stage3Dataset)
    assert isinstance(audit, Stage3PlanAudit)
    audit_rows = {row.job_id: row for row in audit.rows}
    manifest_path = root / dataset.activation_manifest_path
    if _sha(manifest_path.read_bytes()) != dataset.activation_manifest_sha256:
        raise Stage5Error("Stage 3 activation manifest changed after dataset assembly")
    manifest = load_activation_manifest(manifest_path)
    directory = manifest_path.parent
    renders: dict[str, list[ActivationRenderJob]] = defaultdict(list)
    for render in manifest.render_jobs:
        renders[render.plan_job_id].append(render)
    output: list[PlanObservation] = []
    for row in dataset.rows:
        if row.plan_sha256 is None or row.plan_tokens is None:
            continue
        samples: list[SampleOutcome] = []
        audit_row = audit_rows[row.job_id]
        for render in renders[row.job_id]:
            samples.append(
                _stage3_sample(render, directory, dataset.activation_manifest_sha256, root)
            )
        output.append(
            PlanObservation(
                source=SourceStage.STAGE3,
                model_scope=ModelScope.LOCAL_QWEN,
                run_id=dataset.run_id,
                task_id=row.task_id,
                family=row.family,
                split=row.split,
                plan_job_id=row.job_id,
                plan_sha256=row.plan_sha256,
                assigned_policy=row.assigned_policy,
                plan_format=row.plan_format.value,
                concision=row.concision.value,
                plan_tokens=row.plan_tokens,
                document_tokens=row.document_tokens,
                clause_selection=row.clause_selection,
                policy_visibility=row.policy_visibility,
                visible_policy_retained=row.visible_policy_retained,
                irrelevant_clause_ids_included=row.irrelevant_clause_ids_included,
                applicable_clause_ids=audit_row.applicable_clause_ids,
                selected_clause_ids=audit_row.selected_clause_ids,
                audit_confident=(
                    None if row.confidence is None else row.confidence.value == "confident"
                ),
                samples=tuple(sorted(samples, key=lambda sample: sample.sample_index)),
            )
        )
    return output


def _stage3_sample(
    render: ActivationRenderJob, directory: Path, manifest_sha: str, root: Path
) -> SampleOutcome:
    result = _load(CandidateResult, directory / render.result_path)
    outcomes = _empty_outcomes()
    candidate_path = None
    candidate_sha = None
    if result.candidate_path and result.candidate_sha256:
        candidate = (directory / result.candidate_path).resolve()
        _verify_candidate(candidate, result.candidate_sha256, root)
        artifact = _load(
            Stage3EvaluationArtifact, directory / f"jobs/{render.job_id}/evaluation.json"
        )
        if (
            artifact.manifest_sha256 != manifest_sha
            or artifact.candidate_sha256 != result.candidate_sha256
        ):
            raise Stage5Error(f"Stage 3 evaluation provenance mismatch: {render.job_id}")
        outcomes = _evaluation_outcomes(artifact.evaluation)
        candidate_path = _relative(candidate, root)
        candidate_sha = result.candidate_sha256
    return SampleOutcome(
        job_id=render.job_id,
        sample_index=render.render_index,
        generation_status=result.status.value,
        candidate_path=candidate_path,
        candidate_sha256=candidate_sha,
        **outcomes,
    )


def _stage4_rows(
    paths: dict[str, Path],
    loaded: dict[str, StrictModel],
    tasks: dict[str, TaskSpec],
    root: Path,
) -> list[PlanObservation]:
    full = loaded["stage4_full_manifest"]
    assert isinstance(full, Stage4FullRunManifest)
    directory = paths["stage4_full_manifest"].parent
    experiment_path = root / full.experiment_manifest_path
    if _sha(experiment_path.read_bytes()) != full.experiment_manifest_sha256:
        raise Stage5Error("Stage 4 experiment manifest changed")
    experiment = _load(Stage4ExperimentManifest, experiment_path)
    recipient = next(row for row in experiment.recipients if row.split is SplitName.TEST)
    stage3_dataset = loaded["stage3_dataset"]
    assert isinstance(stage3_dataset, Stage3Dataset)
    original_row = next(
        row for row in stage3_dataset.rows if row.job_id == recipient.omitted.job_id
    )
    jobs = [row for row in full.jobs if row.direction_kind is None]
    samples: list[SampleOutcome] = []
    manifest_sha = _sha(paths["stage4_full_manifest"].read_bytes())
    for job in jobs:
        result = _json(directory / job.result_path)
        artifact = _load(Stage4EvaluationArtifact, directory / f"jobs/{job.job_id}/evaluation.json")
        if artifact.manifest_sha256 != manifest_sha or artifact.evaluation is None:
            raise Stage5Error(f"Stage 4 unpatched evaluation is unavailable: {job.job_id}")
        candidate_sha = result.get("candidate_sha256")
        candidate_path = (directory / job.candidate_path).resolve()
        if not isinstance(candidate_sha, str):
            raise Stage5Error(f"Stage 4 candidate hash missing: {job.job_id}")
        _verify_candidate(candidate_path, candidate_sha, root)
        samples.append(
            SampleOutcome(
                job_id=job.job_id,
                sample_index=job.sample_index,
                generation_status=str(result.get("status", "unknown")),
                candidate_path=_relative(candidate_path, root),
                candidate_sha256=candidate_sha,
                **_evaluation_outcomes(artifact.evaluation),
            )
        )
    spec = tasks[recipient.task_id]
    return [
        PlanObservation(
            source=SourceStage.STAGE4,
            model_scope=ModelScope.LOCAL_QWEN,
            run_id=full.run_id,
            task_id=recipient.task_id,
            family=spec.family.value,
            split=SplitName.TEST,
            plan_job_id=recipient.omitted.job_id,
            plan_sha256=recipient.omitted.plan_sha256,
            assigned_policy=recipient.omitted.assigned_policy,
            plan_format=recipient.omitted.plan_format,
            concision=recipient.omitted.concision,
            plan_tokens=recipient.omitted.plan_tokens,
            document_tokens=original_row.document_tokens,
            clause_selection=original_row.clause_selection,
            policy_visibility=recipient.omitted.policy_visibility,
            visible_policy_retained=False,
            irrelevant_clause_ids_included=original_row.irrelevant_clause_ids_included,
            applicable_clause_ids=None,
            selected_clause_ids=None,
            audit_confident=(
                None
                if original_row.confidence is None
                else original_row.confidence.value == "confident"
            ),
            samples=tuple(sorted(samples, key=lambda sample: sample.sample_index)),
        )
    ]


def _stage1_baselines(loaded: dict[str, StrictModel]) -> list[BaselineCell]:
    report = loaded["stage1_surface_report"]
    assert isinstance(report, SurfaceBaselineReport)
    grouped: dict[tuple[str, PolicyValue], list[bool]] = defaultdict(list)
    for row in report.outcomes:
        functional = row.functionality == "pass"
        grouped[(row.task_id, PolicyValue.A)].append(functional and row.policy_a == "pass")
        grouped[(row.task_id, PolicyValue.B)].append(functional and row.policy_b == "pass")
    return [
        BaselineCell(
            source=SourceStage.STAGE1,
            model_scope=ModelScope.HOSTED_KIMI,
            task_id=task,
            policy=policy,
            numerator=sum(values),
            denominator=len(values),
        )
        for (task, policy), values in grouped.items()
    ]


def _stage2_baselines(report_model: StrictModel) -> list[BaselineCell]:
    assert isinstance(report_model, Stage2EvalReport)
    grouped: dict[tuple[str, PolicyValue], list[bool]] = defaultdict(list)
    for row in report_model.direct_rows:
        if row.condition.value != "surface_only_direct":
            continue
        grouped[(row.task_id, PolicyValue.A)].append(
            row.functional and row.policy_a is RawOutcome.PASS
        )
        grouped[(row.task_id, PolicyValue.B)].append(
            row.functional and row.policy_b is RawOutcome.PASS
        )
    return [
        BaselineCell(
            source=SourceStage.STAGE2_FLOOR,
            model_scope=ModelScope.LOCAL_QWEN,
            task_id=task,
            policy=policy,
            numerator=sum(values),
            denominator=len(values),
        )
        for (task, policy), values in grouped.items()
    ]


def _cost_diagnostics(
    paths: dict[str, Path], loaded: dict[str, StrictModel], root: Path
) -> tuple[CostDiagnostic, ...]:
    stage1 = loaded["stage1_behavior"]
    floor = loaded["stage2_floor_report"]
    test = loaded["stage2_test_report"]
    stage3 = loaded["stage3_dataset"]
    stage4 = loaded["stage4_full_manifest"]
    assert isinstance(stage1, BehavioralMetrics)
    assert isinstance(floor, Stage2EvalReport)
    assert isinstance(test, Stage2EvalReport)
    assert isinstance(stage3, Stage3Dataset)
    assert isinstance(stage4, Stage4FullRunManifest)
    stage3_manifest_path = root / stage3.activation_manifest_path
    stage3_manifest = load_activation_manifest(stage3_manifest_path)
    stage3_directory = stage3_manifest_path.parent
    s3_planner_tokens = s3_renderer_tokens = 0
    s3_planner_latency = s3_renderer_latency = 0.0
    for plan_job in stage3_manifest.plan_jobs:
        plan_result = _load(PlanCaptureResult, stage3_directory / plan_job.result_path)
        s3_planner_tokens += plan_result.generation.output_tokens
        s3_planner_latency += plan_result.generation.latency_seconds
    for render_job in stage3_manifest.render_jobs:
        render_result = _load(CandidateResult, stage3_directory / render_job.result_path)
        if render_result.generation is not None:
            s3_renderer_tokens += render_result.generation.output_tokens
            s3_renderer_latency += render_result.generation.latency_seconds
    stage4_directory = paths["stage4_full_manifest"].parent
    s4_tokens = 0
    s4_latency = 0.0
    for full_job in stage4.jobs:
        full_result = _load(Stage4GenerationRecord, stage4_directory / full_job.result_path)
        s4_tokens += full_result.generation.output_tokens
        s4_latency += full_result.generation.latency_seconds
    return (
        CostDiagnostic(
            source=SourceStage.STAGE1,
            model_scope=ModelScope.HOSTED_KIMI,
            scope="natural planner plus renderer matrix",
            planner_output_tokens=stage1.planner_output_tokens,
            planner_reasoning_tokens=stage1.planner_reasoning_tokens,
            renderer_output_tokens=stage1.renderer_output_tokens,
            total_generated_tokens=stage1.total_generated_tokens,
            planner_latency_seconds=stage1.planner_latency_seconds,
            renderer_latency_seconds=stage1.renderer_latency_seconds,
        ),
        *_stage2_cost(SourceStage.STAGE2_FLOOR, floor),
        *_stage2_cost(SourceStage.STAGE2_TEST, test),
        CostDiagnostic(
            source=SourceStage.STAGE3,
            model_scope=ModelScope.LOCAL_QWEN,
            scope="complete activation-dataset planner and renderer generation",
            planner_output_tokens=s3_planner_tokens,
            planner_reasoning_tokens=0,
            renderer_output_tokens=s3_renderer_tokens,
            total_generated_tokens=s3_planner_tokens + s3_renderer_tokens,
            planner_latency_seconds=round(s3_planner_latency, 3),
            renderer_latency_seconds=round(s3_renderer_latency, 3),
        ),
        CostDiagnostic(
            source=SourceStage.STAGE4,
            model_scope=ModelScope.LOCAL_QWEN,
            scope="all 17 full-run conditions; generation only",
            planner_output_tokens=0,
            planner_reasoning_tokens=0,
            renderer_output_tokens=s4_tokens,
            total_generated_tokens=s4_tokens,
            planner_latency_seconds=0.0,
            renderer_latency_seconds=round(s4_latency, 3),
        ),
    )


def _stage2_cost(source: SourceStage, report: Stage2EvalReport) -> tuple[CostDiagnostic]:
    return (
        CostDiagnostic(
            source=source,
            model_scope=ModelScope.LOCAL_QWEN,
            scope=f"complete {report.kind.value} generation matrix",
            planner_output_tokens=report.planner_output_tokens,
            planner_reasoning_tokens=0,
            renderer_output_tokens=report.renderer_output_tokens,
            total_generated_tokens=report.planner_output_tokens + report.renderer_output_tokens,
            planner_latency_seconds=report.planner_latency_seconds,
            renderer_latency_seconds=report.renderer_latency_seconds,
        ),
    )


def _evaluation_outcomes(evaluation: EvaluationResult) -> dict[str, RawOutcome]:
    def outcome(status: RunStatus) -> RawOutcome:
        if status is RunStatus.PASSED:
            return RawOutcome.PASS
        if status is RunStatus.SKIPPED and evaluation.compile.status is RunStatus.PASSED:
            return RawOutcome.NOT_APPLICABLE
        return RawOutcome.FAIL

    return {
        "compilation": outcome(evaluation.compile.status),
        "functionality": outcome(evaluation.suites[TestSuiteKind.FUNCTIONALITY].status),
        "policy_a": outcome(evaluation.suites[TestSuiteKind.POLICY_A].status),
        "policy_b": outcome(evaluation.suites[TestSuiteKind.POLICY_B].status),
        "original_security": outcome(evaluation.suites[TestSuiteKind.ORIGINAL_SECURITY].status),
    }


def _empty_outcomes() -> dict[str, RawOutcome]:
    return {
        "compilation": RawOutcome.NOT_RUN,
        "functionality": RawOutcome.NOT_RUN,
        "policy_a": RawOutcome.NOT_RUN,
        "policy_b": RawOutcome.NOT_RUN,
        "original_security": RawOutcome.NOT_RUN,
    }


def _task_splits(config: Stage2Config) -> dict[SplitName, tuple[str, ...]]:
    return {
        SplitName.TRAIN: tuple(config.split.train),
        SplitName.DEV: tuple(config.split.dev),
        SplitName.TEST: tuple(config.split.test),
    }


def _verify_candidate(path: Path, expected: str, root: Path) -> None:
    if not path.is_relative_to(root) or not path.is_file() or _sha(path.read_bytes()) != expected:
        raise Stage5Error(f"candidate path/hash mismatch: {path}")


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise Stage5Error(f"artifact must live inside repository: {path}")
    return resolved.relative_to(root).as_posix()


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Stage5Error(f"cannot load JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise Stage5Error(f"expected an object in {path}")
    return value


def _load(model: type[ModelT], path: Path) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise Stage5Error(f"cannot load {model.__name__} from {path}: {error}") from error


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_model(path: Path, model: StrictModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise Stage5Error(f"refusing to overwrite {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(model.model_dump_json(indent=2) + "\n")
