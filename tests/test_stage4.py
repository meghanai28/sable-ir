from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from sable_ir.schema import PolicyValue, SandboxConfig
from sable_ir.stage1_analysis import PolicyVisibility
from sable_ir.stage2 import DesignMode, SplitName, load_stage2_config
from sable_ir.stage2_local import AdapterRef
from sable_ir.stage4 import (
    MATCHED_NULL_CONTROLS,
    DirectionArtifact,
    DirectionKind,
    DirectionRole,
    FullRunJob,
    HookSpecification,
    InterventionMode,
    RecipientCandidate,
    SanityPairResult,
    SelectedRecipient,
    Stage4DirectionSet,
    Stage4ExperimentManifest,
    Stage4FullRunManifest,
    _is_omitted,
    _save_random_orthogonal,
    direction_role,
    load_stage4_config,
    select_stage4_sanity,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64


def test_stage4_config_is_frozen_to_one_task_case_study() -> None:
    config = load_stage4_config(ROOT / "config/stage4.toml")
    assert config.dev_task_id == "ssrf_redirect"
    assert config.heldout_task_id == "path_symlink_archive"
    assert config.thresholds.full_samples_per_condition == 16
    assert config.thresholds.target_functionality_max_lost_outputs == 1
    assert {
        DirectionKind.RANDOM_ORTHOGONAL,
        DirectionKind.UNRELATED_SECURITY_FACT,
        DirectionKind.PARAPHRASE_IDENTITY,
        DirectionKind.LEXICAL_FRAMING,
    } == MATCHED_NULL_CONTROLS
    assert direction_role(DirectionKind.FULL_VECTOR_SAME_TASK) is DirectionRole.POSITIVE_ORACLE


def test_omitted_recipient_must_come_from_paraphrase_set_2() -> None:
    base = dict(
        job_id="job",
        task_id="task",
        split=SplitName.TEST,
        assigned_policy=PolicyValue.A,
        plan_format="structured",
        concision="minimal",
        policy_visibility=PolicyVisibility.OMITTED,
        plan_tokens=20,
        plan_sha256=SHA,
        plan="SOURCE\nmeaningful neutral plan\nEND_PLAN",
    )
    assert _is_omitted(RecipientCandidate(paraphrase_set="set2", **base))
    assert not _is_omitted(RecipientCandidate(paraphrase_set="set1", **base))


def test_seeded_random_control_is_orthogonal(tmp_path: Path) -> None:
    target = np.arange(1, 9, dtype=np.float32)
    target_path = tmp_path / "target.npy"
    output = tmp_path / "random.npy"
    np.save(target_path, target)
    dot = _save_random_orthogonal(target_path, output, 7)
    random = np.load(output)
    target /= np.linalg.norm(target)
    assert dot < 1e-5
    assert abs(float(random @ target)) < 1e-5
    assert np.linalg.norm(random) == pytest.approx(1.0)


def test_direction_set_requires_all_materialized_controls() -> None:
    artifact = DirectionArtifact(
        kind=DirectionKind.POLICY_ORIENTATION,
        role=direction_role(DirectionKind.POLICY_ORIENTATION),
        layer=20,
        path="direction.npy",
        sha256=SHA,
        derivation="test",
        centroids=(-1.0, 1.0),
    )
    with pytest.raises(ValidationError, match="every target/control"):
        Stage4DirectionSet(
            created_at="2026-09-03T00:00:00+00:00",
            experiment_manifest_sha256=SHA,
            artifacts=(artifact,),
            target_random_absolute_dot=0.0,
            decoder_block_container_module="model.language_model.layers",
            expected_num_layers=32,
        )


def test_full_run_requires_common_random_number_seed_pairing() -> None:
    artifacts = tuple(
        DirectionArtifact(
            kind=kind,
            role=direction_role(kind),
            layer=20,
            path=f"{kind.value}.npy",
            sha256=SHA,
            derivation="test",
            centroids=(-1.0, 1.0)
            if kind
            in {
                DirectionKind.POLICY_ORIENTATION,
                DirectionKind.UNRELATED_TASK_VALUE,
                DirectionKind.PREREGISTERED_EARLY_LAYER,
            }
            else None,
        )
        for kind in DirectionKind
    )
    hooks = {
        kind: HookSpecification(
            module=f"model.language_model.layers.{artifact.layer}",
            layer=artifact.layer,
            token_index=42,
            downstream_layers_receiving_edit=11,
        )
        for kind, artifact in zip(DirectionKind, artifacts, strict=True)
    }
    jobs = []
    conditions = [(None, None)] + [
        (kind, policy) for kind in DirectionKind for policy in PolicyValue
    ]
    for kind, policy in conditions:
        for sample, seed in ((0, 101), (1, 202)):
            condition = "unpatched" if kind is None else f"{kind.value}-{policy.value}"
            jobs.append(
                FullRunJob(
                    job_id=f"job-{condition}-{sample}",
                    task_id="task",
                    direction_kind=kind,
                    target_policy=policy,
                    mode=InterventionMode.SINGLE_POSITION_SUBSPACE,
                    strength_multiplier=1.0,
                    sample_index=sample,
                    seed=seed,
                    prompt="prompt",
                    prompt_sha256=SHA,
                    candidate_path=f"jobs/{condition}-{sample}/candidate.py",
                    result_path=f"jobs/{condition}-{sample}/result.json",
                )
            )
    manifest = Stage4FullRunManifest(
        run_id="run",
        created_at="2026-09-03T00:00:00+00:00",
        experiment_manifest_path="experiment.json",
        experiment_manifest_sha256=SHA,
        sanity_selection_sha256=SHA,
        direction_set_path="directions.json",
        direction_set_sha256=SHA,
        resolved_direction_artifacts=artifacts,
        selected_strength_multiplier=1.0,
        samples_per_condition=2,
        sandbox=SandboxConfig(),
        jobs=tuple(jobs),
        hook_by_direction=hooks,
        paired_seed_by_sample_index={0: 101, 1: 202},
    )
    broken = list(manifest.jobs)
    broken[-1] = broken[-1].model_copy(update={"seed": 303})
    with pytest.raises(ValidationError, match="share the fixed seed"):
        Stage4FullRunManifest.model_validate(
            {**manifest.model_dump(), "jobs": [row.model_dump() for row in broken]}
        )


def test_sanity_selection_requires_and_binds_exact_matrix(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    shutil.copy(ROOT / "config/stage4.toml", tmp_path / "config/stage4.toml")
    stage2 = load_stage2_config(ROOT / "config/stage2.toml")
    direction_artifacts = tuple(
        DirectionArtifact(
            kind=kind,
            role=direction_role(kind),
            layer=20,
            path=None,
            sha256=None,
            derivation="test",
            centroids=(-1.0, 1.0) if kind is DirectionKind.POLICY_ORIENTATION else None,
        )
        for kind in DirectionKind
    )

    def candidate(job: str, split: SplitName, policy: PolicyValue) -> RecipientCandidate:
        return RecipientCandidate(
            job_id=job,
            task_id="ssrf_redirect" if split is SplitName.DEV else "path_symlink_archive",
            split=split,
            assigned_policy=policy,
            paraphrase_set="set2",
            plan_format="structured",
            concision="full",
            policy_visibility=PolicyVisibility.PRESERVED,
            plan_tokens=20,
            plan_sha256=SHA,
            plan="SOURCE\nplan\nEND_PLAN",
        )

    recipients = []
    for split in (SplitName.DEV, SplitName.TEST):
        a = candidate(f"{split.value}-a", split, PolicyValue.A)
        b = candidate(f"{split.value}-b", split, PolicyValue.B)
        omitted = candidate(f"{split.value}-omitted", split, PolicyValue.A).model_copy(
            update={
                "concision": "minimal",
                "policy_visibility": PolicyVisibility.OMITTED,
            }
        )
        recipients.append(
            SelectedRecipient(
                split=split,
                task_id=a.task_id,
                explicit_a=a,
                explicit_b=b,
                omitted=omitted,
            )
        )
    experiment = Stage4ExperimentManifest(
        run_id="test",
        created_at="2026-09-03T00:00:00+00:00",
        design_mode=DesignMode.PILOT,
        pilot=True,
        config_path="config/stage4.toml",
        config_sha256=SHA,
        stage2_config_path="config/stage2.toml",
        stage2_config_sha256=SHA,
        stage3_activation_manifest_path="artifacts/stage3/manifest.json",
        stage3_activation_manifest_sha256=SHA,
        stage3_dataset_sha256=SHA,
        stage3_selection_sha256=SHA,
        stage3_heldout_sha256=SHA,
        stage3_report_sha256=SHA,
        recipient_audit_sha256=SHA,
        model=stage2.model,
        planner_adapter=AdapterRef(
            directory="adapter",
            adapter_file_sha256s={"adapter.safetensors": SHA},
            training_run_id="train",
            global_step=1,
            training_stage1_gate_override=None,
        ),
        selected_layer=20,
        centroids=(-1.0, 1.0),
        direction_artifacts=direction_artifacts,
        strength_multipliers=(0.5, 1.0, 1.5),
        recipients=tuple(recipients),
        unrelated_security_fact_a="strict sessions",
        unrelated_security_fact_b="permissive sessions",
        sandbox=SandboxConfig(),
    )
    experiment_path = tmp_path / "experiment.json"
    experiment_path.write_text(experiment.model_dump_json(indent=2), encoding="utf-8")
    results = []
    for strength in experiment.strength_multipliers:
        for kind in (
            DirectionKind.POLICY_ORIENTATION,
            DirectionKind.RANDOM_ORTHOGONAL,
            DirectionKind.UNRELATED_SECURITY_FACT,
            DirectionKind.PARAPHRASE_IDENTITY,
            DirectionKind.LEXICAL_FRAMING,
        ):
            raw = tmp_path / f"{kind.value}-{strength}.npz"
            raw.write_bytes(b"raw")
            target = kind is DirectionKind.POLICY_ORIENTATION
            row = SanityPairResult(
                run_id="test",
                experiment_manifest_sha256=hashlib.sha256(experiment_path.read_bytes()).hexdigest(),
                direction_set_sha256=SHA,
                divergence_spec_sha256=SHA,
                prompt_sha256=SHA,
                task_id="ssrf_redirect",
                direction_kind=kind,
                strength_multiplier=strength,
                unpatched_to_a_kl=0.1,
                unpatched_to_b_kl=0.1,
                a_vs_b_js_divergence=0.2 if target else 0.01,
                teacher_forced_a_minus_b_log_odds_gap=0.2 if target else 0.0,
                policy_relevant_token_logit_changes={"redirect": 0.1},
                raw_distribution_path=raw.relative_to(tmp_path).as_posix(),
                raw_distribution_sha256=hashlib.sha256(b"raw").hexdigest(),
            )
            path = tmp_path / f"{kind.value}-{strength}.json"
            path.write_text(row.model_dump_json(indent=2), encoding="utf-8")
            results.append(path)
    output = tmp_path / "selection.json"
    selection = select_stage4_sanity(experiment_path, tuple(results), tmp_path, output)
    assert selection.passed
    assert selection.selected_strength_multiplier == 0.5
    assert len(selection.sanity_result_sha256s) == 15
