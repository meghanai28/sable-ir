from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from sable_ir.schema import PolicyValue
from sable_ir.scoring import RawOutcome
from sable_ir.stage1_analysis import ClauseSelection, PolicyVisibility
from sable_ir.stage2 import SplitName
from sable_ir.stage5 import (
    BaselineCell,
    ModelScope,
    PlanObservation,
    SampleOutcome,
    SourceStage,
    Stage5AnalysisConfig,
    Stage5ObservationDataset,
    load_stage5_config,
    validate_stage5_config,
)
from sable_ir.stage5_analysis import (
    AnalysisStatus,
    CollisionIndex,
    DevelopmentCollisionAudit,
    build_collision_index,
    build_stage5_metrics,
    freeze_collision_taxonomy,
    prepare_development_collision_audit,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64


def _sample(index: int, category: str, candidate: Path | None = None) -> SampleOutcome:
    functional = category != "nonfunctional"
    a = category in ("A", "both")
    b = category in ("B", "both")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate else None
    return SampleOutcome(
        job_id=f"render-{index}",
        sample_index=index,
        generation_status="generated",
        compilation=RawOutcome.PASS,
        functionality=RawOutcome.PASS if functional else RawOutcome.FAIL,
        policy_a=RawOutcome.PASS if a else RawOutcome.FAIL,
        policy_b=RawOutcome.PASS if b else RawOutcome.FAIL,
        original_security=RawOutcome.FAIL,
        candidate_path=None if candidate is None else candidate.as_posix(),
        candidate_sha256=digest,
    )


def _plan(
    samples: tuple[SampleOutcome, ...],
    *,
    task: str = "task_one",
    split: SplitName = SplitName.TRAIN,
    visible: bool = False,
) -> PlanObservation:
    return PlanObservation(
        source=SourceStage.STAGE1,
        model_scope=ModelScope.HOSTED_KIMI,
        run_id="run",
        task_id=task,
        family="path_traversal",
        split=split,
        plan_job_id=f"{task}-plan",
        plan_sha256=hashlib.sha256(f"{task}-plan".encode()).hexdigest(),
        assigned_policy=PolicyValue.A,
        plan_format="structured",
        concision="minimal",
        plan_tokens=32,
        content_tokens_without_fixed_labels=20,
        document_tokens=200,
        clause_selection=ClauseSelection.CORRECT,
        policy_visibility=(PolicyVisibility.PRESERVED if visible else PolicyVisibility.OMITTED),
        visible_policy_retained=visible,
        irrelevant_clause_ids_included=(),
        applicable_clause_ids=("path_policy",),
        selected_clause_ids=("path_policy",),
        audit_confident=True,
        samples=samples,
    )


def _write_dataset(
    path: Path,
    rows: tuple[PlanObservation, ...],
    stage3_report: Path | None = None,
    stage4_report: Path | None = None,
) -> None:
    tasks = {row.task_id for row in rows}
    baselines = tuple(
        BaselineCell(
            source=SourceStage.STAGE1,
            model_scope=ModelScope.HOSTED_KIMI,
            task_id=task,
            policy=policy,
            numerator=1,
            denominator=4,
        )
        for task in tasks
        for policy in PolicyValue
    )
    dataset = Stage5ObservationDataset(
        created_at="2026-09-03T00:00:00+00:00",
        input_manifest_sha256=SHA,
        prior_report_sha256={
            "stage2_test": SHA,
            "stage3": SHA
            if stage3_report is None
            else hashlib.sha256(stage3_report.read_bytes()).hexdigest(),
            "stage4": SHA
            if stage4_report is None
            else hashlib.sha256(stage4_report.read_bytes()).hexdigest(),
        },
        rows=rows,
        surface_baselines=baselines,
        cost_diagnostics=(),
    )
    path.write_text(dataset.model_dump_json(indent=2), encoding="utf-8")


def test_config_is_analysis_only_and_does_not_require_finished_artifacts() -> None:
    config = load_stage5_config(ROOT / "config/stage5.toml")
    summary = validate_stage5_config(ROOT / "config/stage5.toml", ROOT)
    assert summary.analysis_only
    assert summary.configured_inputs == 18
    assert summary.tasks == 5
    assert config.analysis.ambiguity_min_functional_classifiable == 8


def test_ambiguity_floor_hu_and_task_clustering(tmp_path: Path) -> None:
    rows = (
        _plan(tuple(_sample(i, "A" if i < 4 else "B") for i in range(8))),
        _plan(
            tuple(_sample(i + 20, "A") for i in range(4)),
            task="task_two",
        ),
    )
    stage3 = tmp_path / "stage3.json"
    stage4 = tmp_path / "stage4.json"
    stage3.write_text("{}", encoding="utf-8")
    stage4.write_text("{}", encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_dataset(observations, rows, stage3, stage4)
    output = tmp_path / "metrics.json"
    report = build_stage5_metrics(
        observations,
        Stage5AnalysisConfig(bootstrap_replicates=1000, bootstrap_seed=1, top_k=(1, 3, 5)),
        stage3,
        stage4,
        output,
    )
    source = report.source_metrics[0]
    first = next(row for row in source.ambiguity_rows if row.task_id == "task_one")
    assert report.status is AnalysisStatus.COMPLETE
    assert first.support_status == "supported"
    assert first.q_a == 0.5
    assert first.a_ab == 1.0
    assert first.collision
    assert source.capability.functionality.independent_task_clusters == 2
    assert source.excess_hidden_use_by_policy[PolicyValue.A].eligible_task_clusters == 2


def test_both_policy_output_invalidates_metrics(tmp_path: Path) -> None:
    stage3 = tmp_path / "stage3.json"
    stage4 = tmp_path / "stage4.json"
    stage3.write_text("{}", encoding="utf-8")
    stage4.write_text("{}", encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_dataset(observations, (_plan((_sample(0, "both"),)),), stage3, stage4)
    report = build_stage5_metrics(
        observations,
        Stage5AnalysisConfig(bootstrap_replicates=1000, bootstrap_seed=1, top_k=(1,)),
        stage3,
        stage4,
        tmp_path / "metrics.json",
    )
    assert report.status is AnalysisStatus.INVALID_TASK_OR_TESTS
    assert report.total_functional_outputs_passing_both_mutually_exclusive_suites == 1


def test_development_audit_withholds_heldout_until_taxonomy_freeze(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("POLICY = 'A'\n", encoding="utf-8")
    b.write_text("POLICY = 'B'\n", encoding="utf-8")

    def collision_plan(task: str, split: SplitName) -> PlanObservation:
        first = _sample(0, "A", a).model_copy(update={"candidate_path": "a.py"})
        second = _sample(1, "B", b).model_copy(update={"candidate_path": "b.py"})
        return _plan((first, second), task=task, split=split)

    observations = tmp_path / "observations.json"
    _write_dataset(
        observations,
        (
            collision_plan("development_task", SplitName.DEV),
            collision_plan("heldout_task", SplitName.TEST),
        ),
    )
    index_path = tmp_path / "collision-index.json"
    index = build_collision_index(observations, index_path)
    assert len(index.records) == 2
    audit_path = tmp_path / "development-audit.json"
    audit = prepare_development_collision_audit(
        index_path,
        ROOT / "data/stage5/collision-rubric.json",
        tmp_path,
        audit_path,
        tmp_path / "development-diffs",
    )
    assert len(audit.rows) == 1
    assert audit.rows[0].task_id == "development_task"
    completed_row = audit.rows[0].model_copy(
        update={
            "first_policy_relevant_behavioral_divergence": "constant value",
            "category_id": "policy_constant",
            "category_definition": "The first policy behavior is a fixed constant.",
            "smallest_additional_plan_distinction": "State the required policy constant.",
            "same_distinction_explains_collision_ids": (),
        }
    )
    completed = DevelopmentCollisionAudit(
        created_at=audit.created_at,
        collision_index_sha256=audit.collision_index_sha256,
        collision_rubric_sha256=audit.collision_rubric_sha256,
        instructions=audit.instructions,
        rows=(completed_row,),
        reviewer="auditor",
        completed_at="2026-09-03T00:00:00+00:00",
    )
    completed_path = tmp_path / "development-complete.json"
    completed_path.write_text(completed.model_dump_json(indent=2), encoding="utf-8")
    taxonomy = freeze_collision_taxonomy(
        completed_path,
        ROOT / "data/stage5/collision-rubric.json",
        tmp_path / "taxonomy.json",
    )
    assert taxonomy.categories[0].category_id == "policy_constant"


def test_collision_index_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CollisionIndex.model_validate(
            {
                "schema_version": 1,
                "created_at": "now",
                "observations_sha256": SHA,
                "natural_samples_only": True,
                "exact_task_and_plan_grouping": True,
                "invalid_both_policy_outputs": 0,
                "records": [],
                "leak_heldout": True,
            }
        )
