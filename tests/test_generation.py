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
from sable_ir.provider import ModelRequest, ProviderResponse, TokenUsage
from sable_ir.schema import Stage0Condition


class FakeGenerationClient:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(
            request_id="mock-request",
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
    jobs = {job.condition: job for job in manifest.jobs if job.task_id == "path_symlink_report"}
    assert (
        jobs[Stage0Condition.RELEVANT_CLAUSE_ONLY_A].seed
        == jobs[Stage0Condition.RELEVANT_CLAUSE_ONLY_B].seed
    )
    assert (
        jobs[Stage0Condition.FULL_DOCUMENT_A].seed
        == jobs[Stage0Condition.FULL_DOCUMENT_B].seed
    )
    assert (
        jobs[Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A].seed
        == jobs[Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_B].seed
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


def test_preflight_never_contacts_provider_and_never_returns_key(monkeypatch) -> None:
    config = load_stage0_config(Path("config/stage0.toml"))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-secret")

    result = provider_preflight(config.hosted_qwen)

    assert result.ready_for_requests
    assert "sk-test-secret" not in result.model_dump_json()
