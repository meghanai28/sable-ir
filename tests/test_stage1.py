from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from sable_ir.config import load_stage1_config
from sable_ir.harness import UnsafeLocalSandbox
from sable_ir.provider import ModelRequest, ProviderError, ProviderResponse, TokenUsage
from sable_ir.schema import Stage1PlanFormat
from sable_ir.stage1 import (
    Stage1Error,
    build_stage1a_status,
    evaluate_stage1_renders,
    extract_plan,
    prepare_stage1_plans,
    prepare_stage1_render_recovery,
    prepare_stage1_renders,
    require_plan_canary,
    require_render_canary,
    run_stage1_plans,
    run_stage1_renders,
)


class FakeStage1Client:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ProviderResponse:
        self.requests.append(request)
        if request.thinking_requested == "enabled":
            if "Use exactly these six labels" in request.prompt:
                content = (
                    "SOURCE: external input\n"
                    "TRUST: untrusted\n"
                    "SINK: requested operation\n"
                    "GUARD: enforce the applicable policy\n"
                    "ORDER: validate before the sink\n"
                    "EFFECT: return the requested result\n"
                    "END_PLAN"
                )
            else:
                content = "Validate the input under the applicable policy before use.\nEND_PLAN"
            reasoning = "selected the applicable clause"
            reasoning_tokens = 7
            output_tokens = 31
        else:
            content = "def read_report(filename: str, reports_root: str) -> str:\n    return ''\n"
            reasoning = ""
            reasoning_tokens = 1
            output_tokens = 18
        return ProviderResponse(
            request_id=f"mock-{len(self.requests)}",
            model=request.model,
            content=content,
            reasoning_content=reasoning,
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=output_tokens,
                total_tokens=100 + output_tokens,
                reasoning_tokens=reasoning_tokens,
            ),
            raw_events=({"id": f"mock-{len(self.requests)}"},),
        )


class FailingClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ModelRequest) -> ProviderResponse:
        del request
        self.calls += 1
        raise ProviderError("simulated provider failure", retryable=True)


class TruncatedRenderClient:
    def generate(self, request: ModelRequest) -> ProviderResponse:
        return ProviderResponse(
            request_id="mock-truncated-render",
            model=request.model,
            content="def read_report(filename: str, reports_root: str) -> str:\n    return ''\n",
            reasoning_content="",
            finish_reason="length",
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=4096,
                total_tokens=4196,
                reasoning_tokens=1,
            ),
            raw_events=({"id": "mock-truncated-render"},),
        )


def test_stage1a_matrix_and_end_to_end_artifact_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    monkeypatch.setattr("sable_ir.stage1._wait_for_request_interval", lambda *_args: None)
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        base = Path(temporary)
        plan_dir = base / "plans"
        plan_manifest = prepare_stage1_plans(config, root, plan_dir, "stage1a-test-plans")

        assert len(plan_manifest.jobs) == 180
        assert len({job.pair_id for job in plan_manifest.jobs}) == 90
        assert {job.thinking_requested for job in plan_manifest.jobs} == {"enabled"}
        assert all((plan_dir / job.request_path).is_file() for job in plan_manifest.jobs)
        client = FakeStage1Client()
        plan_summary = run_stage1_plans(plan_dir / "manifest.json", client)

        assert plan_summary.generated == 180
        assert plan_summary.pending == 0
        assert all(request.max_completion_tokens == 32_768 for request in client.requests)
        require_plan_canary(plan_dir / "manifest.json")

        render_dir = base / "renders"
        render_manifest = prepare_stage1_renders(
            config,
            root,
            plan_dir / "manifest.json",
            render_dir,
            "stage1a-test-renders",
        )

        assert len(render_manifest.jobs) == 720
        assert len({job.source_plan_job_id for job in render_manifest.jobs}) == 180
        assert all(
            sum(
                other.source_plan_job_id == job.source_plan_job_id for other in render_manifest.jobs
            )
            == 4
            for job in render_manifest.jobs[::4]
        )
        first = render_manifest.jobs[0]
        render_client = FakeStage1Client()
        render_summary = run_stage1_renders(
            render_dir / "manifest.json", render_client, job_id=first.job_id
        )
        assert render_summary.generated == 1
        assert render_client.requests[0].thinking_requested == "disabled"
        assert render_client.requests[0].max_completion_tokens == 4096

        evaluation = evaluate_stage1_renders(
            render_dir / "manifest.json",
            root,
            UnsafeLocalSandbox(config.sandbox),
            job_id=first.job_id,
        )
        assert evaluation.evaluated == 1
        require_render_canary(render_dir / "manifest.json")
        status = build_stage1a_status(plan_dir / "manifest.json", render_dir / "manifest.json")
        assert status.generated_plans == 180
        assert status.generated_renders == 1
        assert status.evaluated_renders == 1
        assert not status.complete


def test_renderer_recovery_carries_exact_results_and_authorizes_one_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    monkeypatch.setattr("sable_ir.stage1._wait_for_request_interval", lambda *_args: None)
    with tempfile.TemporaryDirectory(dir=root / "artifacts") as temporary:
        base = Path(temporary)
        plan_dir = base / "plans"
        prepare_stage1_plans(config, root, plan_dir, "stage1-render-recovery-plans")
        run_stage1_plans(plan_dir / "manifest.json", FakeStage1Client())

        source_dir = base / "source-renders"
        source_manifest = prepare_stage1_renders(
            config,
            root,
            plan_dir / "manifest.json",
            source_dir,
            "stage1-render-recovery-source",
        )
        carried_job, retry_job = source_manifest.jobs[:2]
        run_stage1_renders(
            source_dir / "manifest.json", FakeStage1Client(), job_id=carried_job.job_id
        )
        run_stage1_renders(
            source_dir / "manifest.json", TruncatedRenderClient(), job_id=retry_job.job_id
        )

        source_result = source_dir / carried_job.result_path
        source_result_bytes = source_result.read_bytes()
        retry_attempt = source_dir / "jobs" / retry_job.job_id / "attempts" / "attempt-01.json"
        retry_attempt_hash = hashlib.sha256(retry_attempt.read_bytes()).hexdigest()
        recovery_dir = base / "recovery-renders"
        recovery = prepare_stage1_render_recovery(
            config,
            root,
            source_dir / "manifest.json",
            recovery_dir,
            "stage1-render-recovery",
            (retry_job.job_id,),
        )

        assert recovery.carried_forward_result_sha256s == {
            carried_job.job_id: hashlib.sha256(source_result_bytes).hexdigest()
        }
        assert (recovery_dir / carried_job.result_path).read_bytes() == source_result_bytes
        assert not (recovery_dir / retry_job.result_path).exists()
        assert not (recovery_dir / "jobs" / retry_job.job_id / "attempts").exists()
        assert recovery.execution_order is not None
        assert retry_job.job_id in recovery.execution_order
        authorization = recovery.manual_retry_authorizations[0]
        assert authorization.job_id == retry_job.job_id
        assert authorization.reason == "truncated_renderer_output"
        assert authorization.prior_attempt_sha256 == retry_attempt_hash
        assert authorization.prior_result_sha256 == hashlib.sha256(
            (source_dir / retry_job.result_path).read_bytes()
        ).hexdigest()

        summary = run_stage1_renders(
            recovery_dir / "manifest.json", FakeStage1Client(), job_id=retry_job.job_id
        )
        assert summary.generated == 1
        attempt = json.loads(
            (
                recovery_dir
                / "jobs"
                / retry_job.job_id
                / "attempts"
                / "attempt-01.json"
            ).read_text()
        )
        assert attempt["authorized_lineage_retry_of_attempt_sha256"] == retry_attempt_hash


def test_plan_parser_requires_marker_and_structured_fields() -> None:
    valid = (
        "SOURCE: x\nTRUST: untrusted\nSINK: y\nGUARD: g\nORDER: before\nEFFECT: result\nEND_PLAN"
    )
    plan, extraction = extract_plan(valid, Stage1PlanFormat.STRUCTURED)
    assert plan.endswith("END_PLAN\n")
    assert extraction == "structured_end_plan"

    with pytest.raises(Stage1Error, match="END_PLAN"):
        extract_plan("SOURCE: x", Stage1PlanFormat.STRUCTURED)
    with pytest.raises(Stage1Error, match="EFFECT"):
        extract_plan(
            "SOURCE: x\nTRUST: t\nSINK: s\nGUARD: g\nORDER: o\nEND_PLAN",
            Stage1PlanFormat.STRUCTURED,
        )


def test_plan_provider_failure_stops_before_later_spend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path.cwd()
    config = load_stage1_config(root / "config/stage1.toml")
    plan_dir = tmp_path / "plans"
    prepare_stage1_plans(config, root, plan_dir, "stage1a-failure-test")
    monkeypatch.setattr("sable_ir.stage1._wait_for_request_interval", lambda *_args: None)
    client = FailingClient()

    summary = run_stage1_plans(plan_dir / "manifest.json", client)

    assert client.calls == 1
    assert summary.failed == 1
    assert summary.pending == 180
    with pytest.raises(Stage1Error, match="already used its single provider attempt"):
        run_stage1_plans(plan_dir / "manifest.json", client)
    assert client.calls == 1
