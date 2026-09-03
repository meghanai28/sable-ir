from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from sable_ir.config import load_stage0_config
from sable_ir.generation import (
    GenerationError,
    GenerationRecord,
    prepare_stage0_dataset_revision,
    prepare_stage0_recovery,
    prepare_stage0_run,
    provider_preflight,
    run_stage0_generation,
    select_manifest_jobs,
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
            reasoning_content=(
                "mock reasoning" if request.thinking_requested == "enabled" else ""
            ),
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=12,
                total_tokens=112,
                reasoning_tokens=3 if request.thinking_requested == "enabled" else 0,
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


class RateLimitedGenerationClient:
    def generate(self, request: ModelRequest) -> ProviderResponse:
        del request
        raise ProviderError("Kimi HTTP 429: test rate limit", retryable=True)


class TimedOutGenerationClient:
    def generate(self, request: ModelRequest) -> ProviderResponse:
        del request
        raise ProviderError("Kimi SSE response exceeded the configured wall-time limit")


def test_prepare_freezes_all_forty_stage0_requests(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"

    manifest = prepare_stage0_run(config, root, run_directory, "test-run")

    assert len(manifest.jobs) == 40
    assert manifest.schema_version == 10
    assert manifest.generation_harness_version == "stage0-kimi-generation-v6"
    assert manifest.evaluation_harness_version == "stage0-evaluation-v2"
    assert sum(job.thinking_requested == "enabled" for job in manifest.jobs) == 10
    assert {job.condition for job in manifest.jobs} == set(Stage0Condition)
    assert all((run_directory / job.request_path).is_file() for job in manifest.jobs)
    assert (run_directory / "manifest.json").is_file()
    assert all(len(job.upstream_source_revision) == 40 for job in manifest.jobs)
    assert all(len(job.upstream_prompt_sha256) == 64 for job in manifest.jobs)
    assert all(job.upstream_task_id for job in manifest.jobs)
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
    assert jobs[Stage0Condition.ORIGINAL_BENCHMARK].pair_id is None
    assert jobs[Stage0Condition.SURFACE_ONLY_DIRECT].pair_id is None
    paired = {
        job.pair_id
        for condition, job in jobs.items()
        if condition
        not in {
            Stage0Condition.ORIGINAL_BENCHMARK,
            Stage0Condition.SURFACE_ONLY_DIRECT,
        }
    }
    assert paired == {
        "path_symlink_report__relevant_clause_only__pair_00",
        "path_symlink_report__full_document__pair_00",
        "path_symlink_report__native_thinking_full_document__pair_00",
    }
    assert all(not job.provider_seed_supported for job in manifest.jobs)
    assert all(job.provider_seed_sent is None for job in manifest.jobs)
    assert manifest.provider.minimum_request_interval_seconds == 25.0
    assert not manifest.provider.automatic_retries
    assert manifest.carried_forward_result_sha256s == {}
    assert manifest.invalidated_source_result_sha256s == {}
    assert manifest.manual_retry_authorization is None
    assert manifest.dataset_revision is None
    assert manifest.execution_order is None


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
    result = GenerationRecord.model_validate_json(
        (job_root / "result.json").read_text(encoding="utf-8")
    )
    assert result.pair_id is None
    assert not result.provider_seed_supported
    assert result.provider_seed_sent is None
    assert result.thinking_requested == "disabled"
    assert not result.reasoning_content_present


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
    target = next(job for job in manifest.jobs if job.thinking_requested == "enabled")
    client = FakeGenerationClient()

    summary = run_stage0_generation(
        run_directory / "manifest.json",
        client,
        job_id=target.job_id,
    )

    assert summary.generated == 1
    assert len(client.requests) == 1
    assert client.requests[0].job_id == target.job_id
    assert client.requests[0].thinking_requested == "enabled"
    assert client.requests[0].max_completion_tokens == 32_768
    result = GenerationRecord.model_validate_json(
        (run_directory / target.result_path).read_text(encoding="utf-8")
    )
    assert (
        result.pair_id
        == "path_symlink_report__native_thinking_full_document__pair_00"
    )
    assert result.thinking_requested == "enabled"
    assert result.reasoning_content_present


def test_provider_failure_trips_circuit_breaker_before_later_jobs(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    run_directory = tmp_path / "prepared"
    prepare_stage0_run(config, root, run_directory, "circuit-breaker-test")
    client = FailingGenerationClient()

    summary = run_stage0_generation(run_directory / "manifest.json", client)

    assert client.calls == 1
    assert summary.failed == 1
    assert summary.pending == 40
    failed_job = run_directory / "jobs/path_symlink_report__original_benchmark__s00"
    assert (failed_job / "attempts/attempt-01.json").is_file()
    assert not (failed_job / "result.json").exists()

    with pytest.raises(GenerationError, match="already used its single provider attempt"):
        run_stage0_generation(run_directory / "manifest.json", client)
    assert client.calls == 1


def test_generation_paces_request_starts_at_twenty_five_seconds(
    tmp_path: Path, monkeypatch
) -> None:
    root = Path.cwd()
    run_directory = tmp_path / "paced"
    prepare_stage0_run(
        load_stage0_config(root / "config/stage0.toml"),
        root,
        run_directory,
        "paced-test",
    )
    now = [0.0]
    sleeps: list[float] = []
    monkeypatch.setattr("sable_ir.generation.time.monotonic", lambda: now[0])

    def advance(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr("sable_ir.generation.time.sleep", advance)

    summary = run_stage0_generation(
        run_directory / "manifest.json", FakeGenerationClient(), limit=2
    )

    assert summary.generated == 2
    assert sleeps == [25.0]


def test_recovery_hash_links_results_and_authorizes_one_429_attempt(
    tmp_path: Path,
) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    source_directory = tmp_path / "source"
    source = prepare_stage0_run(config, root, source_directory, "source-run")
    completed_job = source.jobs[0]
    retry_job = source.jobs[1]
    run_stage0_generation(
        source_directory / "manifest.json",
        FakeGenerationClient(),
        job_id=completed_job.job_id,
    )
    run_stage0_generation(
        source_directory / "manifest.json",
        RateLimitedGenerationClient(),
        job_id=retry_job.job_id,
    )
    source_result = source_directory / completed_job.result_path
    source_result_bytes = source_result.read_bytes()
    failed_attempt = (
        source_directory / "jobs" / retry_job.job_id / "attempts/attempt-01.json"
    )
    failed_attempt_bytes = failed_attempt.read_bytes()

    recovery_directory = tmp_path / "recovery"
    recovery = prepare_stage0_recovery(
        config,
        root,
        source_directory / "manifest.json",
        recovery_directory,
        "recovery-run",
        retry_job.job_id,
    )

    assert recovery.carried_forward_result_sha256s == {
        completed_job.job_id: hashlib.sha256(source_result_bytes).hexdigest()
    }
    authorization = recovery.manual_retry_authorization
    assert authorization is not None
    assert authorization.job_id == retry_job.job_id
    assert authorization.cooldown_seconds == 65
    assert authorization.additional_attempts == 1
    assert not authorization.automatic_retry
    assert authorization.prior_attempt_sha256 == hashlib.sha256(
        failed_attempt_bytes
    ).hexdigest()
    assert (recovery_directory / completed_job.result_path).read_bytes() == source_result_bytes
    assert failed_attempt.read_bytes() == failed_attempt_bytes
    assert not (recovery_directory / "jobs" / retry_job.job_id / "attempts").exists()


def test_timeout_recovery_changes_only_stream_duration_and_freezes_order(
    tmp_path: Path, monkeypatch
) -> None:
    root = Path.cwd()
    config = load_stage0_config(root / "config/stage0.toml")
    source_config = config.model_copy(
        update={
            "hosted_kimi": config.hosted_kimi.model_copy(
                update={"max_stream_seconds": 600.0}
            )
        }
    )
    source_directory = tmp_path / "timeout-source"
    source = prepare_stage0_run(
        source_config, root, source_directory, "timeout-source"
    )
    retry_job = source.jobs[0]
    clock = iter((0.0, 600.1))
    monkeypatch.setattr("sable_ir.generation.time.monotonic", lambda: next(clock))
    summary = run_stage0_generation(
        source_directory / "manifest.json",
        TimedOutGenerationClient(),
        job_id=retry_job.job_id,
    )
    assert summary.failed == 1
    execution_order = tuple(
        [job.job_id for job in source.jobs if job.job_id != retry_job.job_id]
        + [retry_job.job_id]
    )

    recovery_directory = tmp_path / "timeout-recovery"
    recovery = prepare_stage0_recovery(
        config,
        root,
        source_directory / "manifest.json",
        recovery_directory,
        "timeout-recovery",
        retry_job.job_id,
        cooldown_seconds=0,
        retry_reason="stream_timeout_600",
        execution_order=execution_order,
    )

    assert recovery.provider.max_stream_seconds == 900.0
    assert recovery.provider.thinking_max_completion_tokens == 32_768
    assert recovery.execution_order == execution_order
    assert [
        job.job_id for job in select_manifest_jobs(recovery, use_execution_order=True)
    ] == list(execution_order)
    assert len(select_manifest_jobs(recovery)) == 40
    authorization = recovery.manual_retry_authorization
    assert authorization is not None
    assert authorization.reason == "stream_timeout_600"
    assert authorization.cooldown_seconds == 0
    assert not authorization.automatic_retry


def test_dataset_revision_carries_only_exact_prompt_and_test_inputs(
    tmp_path: Path, monkeypatch
) -> None:
    source_root = Path.cwd()
    repository_root = tmp_path / "repository"
    shutil.copytree(source_root / "tasks", repository_root / "tasks")
    config = load_stage0_config(source_root / "config/stage0.toml")
    source_directory = tmp_path / "source-revision"
    prepare_stage0_run(
        config, repository_root, source_directory, "pre-dataset-revision"
    )
    now = [0.0]
    monkeypatch.setattr("sable_ir.generation.time.monotonic", lambda: now[0])
    monkeypatch.setattr(
        "sable_ir.generation.time.sleep",
        lambda seconds: now.__setitem__(0, now[0] + seconds),
    )
    summary = run_stage0_generation(
        source_directory / "manifest.json", FakeGenerationClient()
    )
    assert summary.generated == 40

    changed_task_id = "path_symlink_archive"
    changed_task_path = repository_root / "tasks" / changed_task_id / "task.json"
    changed_task = json.loads(changed_task_path.read_text(encoding="utf-8"))
    for policy in ("A", "B"):
        for clause in changed_task["documents"][policy]["clauses"]:
            if clause["id"] == "session_cookies":
                clause["text"] += " Sessions must also expire after inactivity."
    changed_task_path.write_text(
        f"{json.dumps(changed_task, indent=2)}\n", encoding="utf-8"
    )
    task_hashes = {
        json.loads((repository_root / relative).read_text(encoding="utf-8"))["id"]: (
            hashlib.sha256((repository_root / relative).read_bytes()).hexdigest()
        )
        for relative in config.task_paths
    }
    audit_path = repository_root / "revised-g7.json"
    audit_path.write_text(
        json.dumps(
            {
                "gate": "G7",
                "audit_complete": True,
                "g7_passed": True,
                "gate_status": "passed",
                "task_sha256": task_hashes,
                "changes": [{"task_id": changed_task_id}],
            }
        ),
        encoding="utf-8",
    )

    revision_directory = tmp_path / "revision"
    revision = prepare_stage0_dataset_revision(
        config,
        repository_root,
        source_directory / "manifest.json",
        audit_path,
        revision_directory,
        "dataset-revision",
        (changed_task_id,),
    )

    assert len(revision.carried_forward_result_sha256s) == 36
    assert len(revision.invalidated_source_result_sha256s) == 4
    assert revision.dataset_revision is not None
    assert revision.dataset_revision.changed_task_ids == (changed_task_id,)
    assert all(
        not (revision_directory / revision.jobs[index].result_path).exists()
        for index in range(len(revision.jobs))
        if revision.jobs[index].job_id in revision.invalidated_source_result_sha256s
    )
    carried_job_id = next(iter(revision.carried_forward_result_sha256s))
    carried_job = next(job for job in revision.jobs if job.job_id == carried_job_id)
    assert (revision_directory / carried_job.result_path).is_file()


def test_preflight_never_contacts_provider_and_never_returns_key(monkeypatch) -> None:
    config = load_stage0_config(Path("config/stage0.toml"))
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-secret")

    result = provider_preflight(config.hosted_kimi)

    assert result.ready_for_requests
    assert "sk-test-secret" not in result.model_dump_json()
