from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from sable_ir.config import load_stage1_config
from sable_ir.provider import ModelRequest, ProviderResponse, TokenUsage
from sable_ir.stage1 import prepare_stage1_plans, run_stage1_plans
from sable_ir.stage1_analysis import build_length_report, prepare_plan_audit
from sable_ir.stage1_controls import (
    ControlPlanAudit,
    ControlPlanKind,
    RendererControlKind,
    prepare_control_plan_audit,
    prepare_control_plan_recovery,
    prepare_control_plans,
    prepare_renderer_control,
    prepare_surface_baseline,
    run_control_plans,
)


class PlannerClient:
    def generate(self, request: ModelRequest) -> ProviderResponse:
        structured = (
            "Use exactly these six labels" in request.prompt
            or "Keep exactly SOURCE" in request.prompt
        )
        content = (
            "SOURCE\ninput\nTRUST\nboundary\nSINK\noperation\nGUARD\npolicy\n"
            "ORDER\nbefore sink\nEFFECT\nresult\nEND_PLAN"
            if structured
            else "Validate the relevant input and apply the selected rule.\nEND_PLAN"
        )
        return ProviderResponse(
            request_id=f"fake-{request.job_id}",
            model=request.model,
            content=content,
            reasoning_content="brief private planning",
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=30,
                total_tokens=40,
                reasoning_tokens=10,
            ),
            raw_events=(),
        )


class FakeEncoding:
    def encode(self, value: str, *, disallowed_special: tuple[()] = ()) -> list[str]:
        del disallowed_special
        return value.split()


class MalformedControlClient:
    def generate(self, request: ModelRequest) -> ProviderResponse:
        return ProviderResponse(
            request_id=f"malformed-{request.job_id}",
            model=request.model,
            content=(
                "SOURCE\nSOURCE: input\nTRUST\nTRUST: boundary\nSINK\nSINK: operation\n"
                "GUARD\nGUARD: policy\nORDER\nORDER: before sink\n"
                "EFFECT\nEFFECT: result\nEND_PLAN"
            ),
            reasoning_content="brief private planning",
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=30,
                total_tokens=40,
                reasoning_tokens=10,
            ),
            raw_events=(),
        )


def _complete_plans(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[object, Path]:
    config = load_stage1_config(root / "config/stage1.toml")
    directory = tmp_path / "plans"
    manifest = prepare_stage1_plans(config, root, directory, "analysis-test-plans")
    monkeypatch.setattr("sable_ir.stage1._wait_for_request_interval", lambda *_args: None)
    result = run_stage1_plans(directory / "manifest.json", PlannerClient())
    assert result.generated == 180
    return manifest, directory / "manifest.json"


def test_length_and_behavior_blinded_audit_cover_complete_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del tmp_path
    root = Path.cwd()
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        base = Path(temporary)
        _manifest, manifest_path = _complete_plans(root, base, monkeypatch)
        monkeypatch.setattr(
            "sable_ir.stage1_analysis.load_kimi_tokenizer", lambda _path: FakeEncoding()
        )
        monkeypatch.setattr(
            "sable_ir.stage1_analysis.fetch_kimi_tokenizer", lambda _path: "b" * 64
        )

        lengths = build_length_report(
            manifest_path, base / "tokenizer.model", base / "lengths.json"
        )
        audit = prepare_plan_audit(manifest_path, root, base / "audit.json")

        assert len(lengths.rows) == 180
        assert len(lengths.nearest_length_matches) == 90
        assert set(lengths.nominal_comparisons_allowed) == {"full", "concise", "minimal"}
        assert len(audit.rows) == 180
        assert all(row.audited_without_generated_code is None for row in audit.rows)
        assert "candidate" not in json.dumps(audit.model_dump(mode="json")).lower()


def test_control_plans_and_renderer_mappings_are_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del tmp_path
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        base = Path(temporary)
        _manifest, natural_path = _complete_plans(root, base, monkeypatch)
        control_directory = base / "control-plans"
        monkeypatch.setattr(
            "sable_ir.stage1_controls.fetch_kimi_tokenizer", lambda _path: "b" * 64
        )
        monkeypatch.setattr(
            "sable_ir.stage1_controls.load_kimi_tokenizer", lambda _path: FakeEncoding()
        )
        controls = prepare_control_plans(
            config,
            root,
            natural_path,
            control_directory,
            "analysis-test-controls",
            base / "tokenizer.model",
        )
        monkeypatch.setattr("sable_ir.stage1_controls._wait", lambda *_args: None)
        summary = run_control_plans(
            control_directory / "manifest.json",
            PlannerClient(),
            root / "config/stage1.toml",
        )

        assert len(controls.jobs) == 120
        assert summary["generated_this_run"] == 120
        assert all(job.kind.value == "wrong_clause" for job in controls.jobs[:60])
        assert all(job.kind.value == "clause_order" for job in controls.jobs[60:])
        wrong_by_task = {
            job.task_id: job
            for job in controls.jobs
            if job.kind.value == "wrong_clause"
        }
        assert wrong_by_task["sql_identifier"].selected_wrong_clause_id == "archive_members"
        assert (
            wrong_by_task["command_executable"].selected_wrong_clause_id
            == "authentication_logs"
        )
        assert all(job.selected_wrong_clause_tokens for job in controls.jobs[:60])
        completed_paths: dict[ControlPlanKind, Path] = {}
        for control_kind in ControlPlanKind:
            template_path = base / f"control-audit-{control_kind.value}-template.json"
            template = prepare_control_plan_audit(
                control_directory / "manifest.json",
                root,
                template_path,
                control_kind,
                base / "tokenizer.model",
            )
            completed_rows = tuple(
                row.model_copy(
                    update={
                        "audited_without_generated_code": True,
                        "selected_clause_ids": (
                            (row.selected_wrong_clause_id,)
                            if row.selected_wrong_clause_id is not None
                            else row.applicable_clause_ids
                        ),
                        "applicable_clause_selected": row.selected_wrong_clause_id is None,
                        "wrong_clause_foregrounded": (
                            True if row.selected_wrong_clause_id is not None else None
                        ),
                        "correct_clause_removed": (
                            True if row.selected_wrong_clause_id is not None else None
                        ),
                        "nonpolicy_information_preserved": (
                            True if row.selected_wrong_clause_id is not None else None
                        ),
                    }
                )
                for row in template.rows
            )
            completed = ControlPlanAudit(
                control_plan_manifest_sha256=template.control_plan_manifest_sha256,
                kind=template.kind,
                tokenizer_revision=template.tokenizer_revision,
                tokenizer_sha256=template.tokenizer_sha256,
                instructions=template.instructions,
                rows=completed_rows,
                reviewer="test reviewer",
                completed_at="2026-09-03T00:00:00+00:00",
            )
            completed_path = base / f"control-audit-{control_kind.value}-complete.json"
            completed_path.write_text(completed.model_dump_json(indent=2), encoding="utf-8")
            completed_paths[control_kind] = completed_path
        for kind in RendererControlKind:
            destination = base / f"renders-{kind.value}"
            manifest = prepare_renderer_control(
                config,
                root,
                natural_path,
                destination,
                f"renders-{kind.value}",
                kind,
                control_plan_manifest_path=(
                    control_directory / "manifest.json"
                    if kind is RendererControlKind.WRONG_CLAUSE
                    else None
                ),
                control_plan_audit_path=(
                    completed_paths[ControlPlanKind.WRONG_CLAUSE]
                    if kind is RendererControlKind.WRONG_CLAUSE
                    else None
                ),
            )
            assert manifest.condition == kind.value
            assert len(manifest.jobs) == 120
            assert manifest.control_mapping_sha256 is not None


def test_control_plan_recovery_carries_results_and_authorizes_named_malformed_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del tmp_path
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        base = Path(temporary)
        _manifest, natural_path = _complete_plans(root, base, monkeypatch)
        monkeypatch.setattr(
            "sable_ir.stage1_controls.fetch_kimi_tokenizer", lambda _path: "b" * 64
        )
        monkeypatch.setattr(
            "sable_ir.stage1_controls.load_kimi_tokenizer", lambda _path: FakeEncoding()
        )
        monkeypatch.setattr("sable_ir.stage1_controls._wait", lambda *_args: None)
        source_directory = base / "control-source"
        source = prepare_control_plans(
            config,
            root,
            natural_path,
            source_directory,
            "control-source",
            base / "tokenizer.model",
        )
        carried_job = source.jobs[0]
        retry_job = next(
            job
            for job in source.jobs
            if job.kind is ControlPlanKind.WRONG_CLAUSE
            and job.plan_format.value == "structured"
        )
        run_control_plans(
            source_directory / "manifest.json",
            PlannerClient(),
            root / "config/stage1.toml",
            job_id=carried_job.job_id,
        )
        run_control_plans(
            source_directory / "manifest.json",
            MalformedControlClient(),
            root / "config/stage1.toml",
            job_id=retry_job.job_id,
        )

        carried_result = source_directory / carried_job.result_path
        carried_bytes = carried_result.read_bytes()
        prior_attempt = (
            source_directory / "jobs" / retry_job.job_id / "attempts" / "attempt-01.json"
        )
        prior_attempt_sha256 = hashlib.sha256(prior_attempt.read_bytes()).hexdigest()
        recovery_directory = base / "control-recovery"
        recovery = prepare_control_plan_recovery(
            config,
            root,
            source_directory / "manifest.json",
            recovery_directory,
            "control-recovery",
            base / "tokenizer.model",
            (retry_job.job_id,),
        )

        assert recovery.carried_forward_result_sha256s == {
            carried_job.job_id: hashlib.sha256(carried_bytes).hexdigest()
        }
        assert (recovery_directory / carried_job.result_path).read_bytes() == carried_bytes
        assert not (recovery_directory / retry_job.result_path).exists()
        assert recovery.execution_order is not None
        assert retry_job.job_id in recovery.execution_order
        authorization = recovery.manual_retry_authorizations[0]
        assert authorization.reason == "malformed_control_plan_output"
        assert authorization.prior_attempt_sha256 == prior_attempt_sha256

        summary = run_control_plans(
            recovery_directory / "manifest.json",
            PlannerClient(),
            root / "config/stage1.toml",
            job_id=retry_job.job_id,
        )
        assert summary["generated_this_run"] == 1
        attempt = json.loads(
            (
                recovery_directory
                / "jobs"
                / retry_job.job_id
                / "attempts"
                / "attempt-01.json"
            ).read_text()
        )
        assert (
            attempt["authorized_lineage_retry_of_attempt_sha256"]
            == prior_attempt_sha256
        )


def test_surface_baseline_freezes_four_stage1_nonthinking_samples_per_task(
    tmp_path: Path,
) -> None:
    del tmp_path
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        directory = Path(temporary) / "surface"
        manifest = prepare_surface_baseline(config, root, directory, "surface-test")

        assert len(manifest.jobs) == 20
        assert {job.sample_index for job in manifest.jobs} == {0, 1, 2, 3}
        for job in manifest.jobs:
            request = json.loads((directory / job.request_path).read_text(encoding="utf-8"))
            model_request = request["model_request"]
            assert model_request["thinking_requested"] == "disabled"
            assert model_request["max_completion_tokens"] == 4096
            assert model_request["pair_id"] is None
