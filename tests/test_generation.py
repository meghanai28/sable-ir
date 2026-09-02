from __future__ import annotations

from pathlib import Path

import pytest

from sable_ir.config import load_stage0_config
from sable_ir.generation import (
    GenerationError,
    prepare_stage0_run,
    provider_preflight,
    run_stage0_generation,
)
from sable_ir.provider import ModelRequest, ProviderError, ProviderResponse, TokenUsage
from sable_ir.schema import Stage0Condition


class FakeGenerationClient:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(
            request_id="mock-request",
            model=request.model,
            content="def generated():\n    return True\n",
            reasoning_content="mock reasoning" if request.enable_thinking else "",
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=12,
                total_tokens=112,
                reasoning_tokens=3 if request.enable_thinking else 0,
            ),
            raw_events=({"request_id": "mock-request", "output": {}},),
        )


class FailingGenerationClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ModelRequest) -> ProviderResponse:
        del request
        self.calls += 1
        raise ProviderError("simulated provider failure", retryable=True)


def test_prepare_freezes_all_forty_stage0_requests(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"

    manifest = prepare_stage0_run(config, root, run_directory, "test-run")

    assert len(manifest.jobs) == 40
    assert sum(job.thinking for job in manifest.jobs) == 10
    assert {job.condition for job in manifest.jobs} == set(Stage0Condition)
    assert all((run_directory / job.request_path).is_file() for job in manifest.jobs)
    assert (run_directory / "manifest.json").is_file()
    assert {
        len(job.test_sha256s)
        for job in manifest.jobs
        if job.condition is Stage0Condition.ORIGINAL_BENCHMARK
    } == {2}
    assert {
        len(job.test_sha256s)
        for job in manifest.jobs
        if job.condition is not Stage0Condition.ORIGINAL_BENCHMARK
    } == {4}
    jobs = {job.condition: job for job in manifest.jobs if job.task_id == "path_symlink_report"}
    assert (
        jobs[Stage0Condition.RELEVANT_CLAUSE_ONLY_A].pair_seed
        == jobs[Stage0Condition.RELEVANT_CLAUSE_ONLY_B].pair_seed
    )
    assert (
        jobs[Stage0Condition.FULL_DOCUMENT_A].pair_seed
        == jobs[Stage0Condition.FULL_DOCUMENT_B].pair_seed
    )
    assert (
        jobs[Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A].pair_seed
        == jobs[Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_B].pair_seed
    )


def test_generation_is_resumable_and_records_immutable_artifacts(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"
    prepare_stage0_run(config, root, run_directory, "resume-test")
    client = FakeGenerationClient()

    first = run_stage0_generation(run_directory / "manifest.json", client, limit=1)
    second = run_stage0_generation(run_directory / "manifest.json", client, limit=1)

    assert first.generated == 1
    assert second.skipped_complete == 1
    assert len(client.requests) == 1
    job_root = run_directory / "jobs" / "path_symlink_report__original_benchmark__s00"
    assert (
        job_root / "candidates/candidate-01.py"
    ).read_text() == "def generated():\n    return True\n"
    assert (job_root / "result.json").is_file()
    assert (job_root / "responses/response-01.json").is_file()
    assert (job_root / "attempts/attempt-01.json").is_file()


def test_generation_refuses_a_changed_frozen_request(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"
    manifest = prepare_stage0_run(config, root, run_directory, "tamper-test")
    request_path = run_directory / manifest.jobs[0].request_path
    request_path.write_text(
        f"{request_path.read_text(encoding='utf-8')}\n",
        encoding="utf-8",
    )
    client = FakeGenerationClient()

    with pytest.raises(GenerationError, match="request changed after preparation"):
        run_stage0_generation(run_directory / "manifest.json", client, limit=1)

    assert client.requests == []


def test_generation_can_target_a_native_thinking_canary(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"
    manifest = prepare_stage0_run(config, root, run_directory, "target-test")
    target = next(job for job in manifest.jobs if job.thinking)
    client = FakeGenerationClient()

    summary = run_stage0_generation(
        run_directory / "manifest.json",
        client,
        job_id=target.job_id,
    )

    assert summary.generated == 1
    assert len(client.requests) == 1
    assert client.requests[0].job_id == target.job_id
    assert client.requests[0].enable_thinking
    assert client.requests[0].max_completion_tokens == 16_384


def test_provider_failure_trips_circuit_breaker_before_later_jobs(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"
    prepare_stage0_run(config, root, run_directory, "circuit-breaker-test")
    client = FailingGenerationClient()

    summary = run_stage0_generation(run_directory / "manifest.json", client)

    assert client.calls == 1
    assert summary.failed == 1
    assert summary.pending == 39
    failed_job = run_directory / "jobs/path_symlink_report__original_benchmark__s00"
    assert (failed_job / "attempts/attempt-01.json").is_file()
    assert not (failed_job / "result.json").exists()

    with pytest.raises(GenerationError, match="already used its single provider attempt"):
        run_stage0_generation(run_directory / "manifest.json", client)
    assert client.calls == 1


def test_preflight_never_contacts_provider_and_never_returns_key(monkeypatch) -> None:
    config = load_stage0_config(Path("config/stage0.toml"))
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-secret")

    result = provider_preflight(config.hosted_kimi)

    assert result.ready_for_requests
    assert "sk-test-secret" not in result.model_dump_json()
