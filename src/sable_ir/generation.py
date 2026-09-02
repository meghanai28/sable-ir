"""Preparation and resumable execution of the hosted Stage 0 generation matrix."""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import Field, ValidationError

from sable_ir.config import load_task
from sable_ir.prompts import assigned_policy, build_task_prompt, build_wire_prompt, prompt_sha256
from sable_ir.provider import DashScopeClient, ModelRequest, ProviderError, ProviderResponse
from sable_ir.schema import (
    STAGE0_CONDITION_SPECS,
    AlibabaQwenConfig,
    PolicyValue,
    Stage0Condition,
    Stage0Config,
    StrictModel,
)


class GenerationError(RuntimeError):
    """Generation preparation or artifact persistence failed."""


class GenerationClient(Protocol):
    def generate(self, request: ModelRequest) -> ProviderResponse: ...


class GenerationStatus(StrEnum):
    GENERATED = "generated"
    TRUNCATED = "truncated"
    MALFORMED = "malformed"


class GenerationJob(StrictModel):
    job_id: str
    task_id: str
    task_path: str
    task_sha256: str
    condition: Stage0Condition
    assigned_policy: PolicyValue | None
    sample_index: int = Field(ge=0)
    seed: int = Field(ge=0, le=2**31 - 1)
    thinking: bool
    request_path: str
    result_path: str


class GenerationManifest(StrictModel):
    schema_version: int = 1
    run_id: str
    created_at: str
    config_sha256: str
    provider: AlibabaQwenConfig
    jobs: tuple[GenerationJob, ...]


class RequestArtifact(StrictModel):
    schema_version: int = 1
    task_id: str
    task_path: str
    task_sha256: str
    condition: Stage0Condition
    assigned_policy: PolicyValue | None
    sample_index: int
    task_prompt: str
    model_request: ModelRequest


class AttemptRecord(StrictModel):
    schema_version: int = 1
    attempt: int
    started_at: str
    finished_at: str
    latency_seconds: float = Field(ge=0)
    succeeded: bool
    retryable: bool = False
    provider_request_id: str | None = None
    error: str | None = None


class GenerationRecord(StrictModel):
    schema_version: int = 1
    job_id: str
    task_id: str
    condition: Stage0Condition
    assigned_policy: PolicyValue | None
    sample_index: int
    seed: int
    model: str
    thinking: bool
    status: GenerationStatus
    extraction: str
    prompt_sha256: str
    content_sha256: str
    candidate_sha256: str | None
    reasoning_sha256: str | None
    reasoning_characters: int
    provider_request_id: str
    finish_reason: str | None
    usage: dict[str, int]
    successful_attempt: int
    raw_response_path: str
    candidate_path: str | None
    reasoning_path: str | None


class RunSummary(StrictModel):
    run_id: str
    total_jobs: int
    generated: int
    truncated: int
    malformed: int
    failed: int
    skipped_complete: int
    pending: int


class ProviderPreflight(StrictModel):
    provider: str
    model: str
    endpoint: str
    api_key_env: str
    api_key_present: bool
    api_key_looks_valid: bool
    ready_for_requests: bool
    note: str


def provider_preflight(config: AlibabaQwenConfig) -> ProviderPreflight:
    value = os.environ.get(config.api_key_env, "")
    present = bool(value.strip())
    looks_valid = present and value.startswith("sk-") and len(value) > 8
    ready = present and looks_valid
    note = (
        "Credential is present; this check does not contact Alibaba or verify account approval."
        if ready
        else f"Set {config.api_key_env} after Alibaba Model Studio access is approved."
    )
    return ProviderPreflight(
        provider=config.provider,
        model=config.model,
        endpoint=f"{config.base_url.rstrip('/')}{config.generation_path}",
        api_key_env=config.api_key_env,
        api_key_present=present,
        api_key_looks_valid=looks_valid,
        ready_for_requests=ready,
        note=note,
    )


def client_from_environment(config: AlibabaQwenConfig) -> DashScopeClient:
    preflight = provider_preflight(config)
    if not preflight.ready_for_requests:
        raise GenerationError(preflight.note)
    return DashScopeClient(config, os.environ[config.api_key_env])


def prepare_stage0_run(
    config: Stage0Config,
    repository_root: Path,
    run_directory: Path,
    run_id: str,
) -> GenerationManifest:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", run_id):
        raise GenerationError("run_id must be 1-80 safe filename characters")
    root = repository_root.resolve()
    run_directory = run_directory.resolve()
    if run_directory.exists() and any(run_directory.iterdir()):
        raise GenerationError(f"run directory is not empty: {run_directory}")
    run_directory.mkdir(parents=True, exist_ok=True)

    jobs: list[GenerationJob] = []
    for task_relative in config.task_paths:
        task_path = (root / task_relative).resolve()
        try:
            task_path.relative_to(root)
        except ValueError as error:
            raise GenerationError(f"task escapes repository root: {task_relative}") from error
        task_bytes = task_path.read_bytes()
        task_hash = hashlib.sha256(task_bytes).hexdigest()
        task = load_task(task_path)
        for condition in config.conditions:
            spec = STAGE0_CONDITION_SPECS[condition]
            for sample_index in range(config.samples_per_condition):
                job_id = f"{task.id}__{condition.value}__s{sample_index:02d}"
                job_root = f"jobs/{job_id}"
                seed = _job_seed(config.seed, task.id, condition, sample_index)
                wire_prompt = build_wire_prompt(task, condition)
                model_request = ModelRequest(
                    job_id=job_id,
                    model=config.hosted_qwen.model,
                    prompt=wire_prompt,
                    prompt_sha256=prompt_sha256(wire_prompt),
                    enable_thinking=spec.thinking,
                    seed=seed,
                    temperature=config.hosted_qwen.temperature,
                    top_p=config.hosted_qwen.top_p,
                    max_tokens=config.hosted_qwen.max_tokens,
                )
                request_artifact = RequestArtifact(
                    task_id=task.id,
                    task_path=task_relative,
                    task_sha256=task_hash,
                    condition=condition,
                    assigned_policy=assigned_policy(condition),
                    sample_index=sample_index,
                    task_prompt=build_task_prompt(task, condition),
                    model_request=model_request,
                )
                request_path = f"{job_root}/request.json"
                _write_json_new(run_directory / request_path, request_artifact)
                jobs.append(
                    GenerationJob(
                        job_id=job_id,
                        task_id=task.id,
                        task_path=task_relative,
                        task_sha256=task_hash,
                        condition=condition,
                        assigned_policy=assigned_policy(condition),
                        sample_index=sample_index,
                        seed=seed,
                        thinking=spec.thinking,
                        request_path=request_path,
                        result_path=f"{job_root}/result.json",
                    )
                )

    config_json = config.model_dump_json(exclude={"artifacts_dir"})
    manifest = GenerationManifest(
        run_id=run_id,
        created_at=_now(),
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
        provider=config.hosted_qwen,
        jobs=tuple(jobs),
    )
    _write_json_new(run_directory / "manifest.json", manifest)
    return manifest


def load_manifest(path: Path) -> GenerationManifest:
    try:
        return GenerationManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise GenerationError(f"could not load generation manifest {path}: {error}") from error


def run_stage0_generation(
    manifest_path: Path,
    client: GenerationClient,
    *,
    limit: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> RunSummary:
    manifest = load_manifest(manifest_path)
    run_directory = manifest_path.resolve().parent
    selected = list(manifest.jobs if limit is None else manifest.jobs[:limit])
    counters = {status.value: 0 for status in GenerationStatus}
    failed = 0
    skipped = 0

    for job in selected:
        result_path = run_directory / job.result_path
        if result_path.exists():
            skipped += 1
            continue
        request_artifact = _load_request(run_directory / job.request_path)
        attempt = _next_attempt(run_directory, job)
        response: ProviderResponse | None = None
        while attempt <= manifest.provider.max_attempts:
            started_at = _now()
            started = time.monotonic()
            try:
                response = client.generate(request_artifact.model_request)
            except ProviderError as error:
                _write_json_new(
                    _attempt_path(run_directory, job, attempt),
                    AttemptRecord(
                        attempt=attempt,
                        started_at=started_at,
                        finished_at=_now(),
                        latency_seconds=time.monotonic() - started,
                        succeeded=False,
                        retryable=error.retryable,
                        error=str(error),
                    ),
                )
                if not error.retryable or attempt >= manifest.provider.max_attempts:
                    break
                delay = manifest.provider.retry_initial_seconds * (2 ** (attempt - 1))
                sleep(min(delay, 60.0))
                attempt += 1
                continue

            raw_path = _response_path(run_directory, job, attempt)
            _write_json_new(raw_path, response)
            _write_json_new(
                _attempt_path(run_directory, job, attempt),
                AttemptRecord(
                    attempt=attempt,
                    started_at=started_at,
                    finished_at=_now(),
                    latency_seconds=time.monotonic() - started,
                    succeeded=True,
                    provider_request_id=response.request_id,
                ),
            )
            break

        if response is None:
            failed += 1
            continue
        try:
            candidate, extraction = extract_python_source(response.content)
            status = (
                GenerationStatus.TRUNCATED
                if response.finish_reason == "length"
                else GenerationStatus.GENERATED
            )
            candidate_hash: str | None = hashlib.sha256(candidate.encode()).hexdigest()
            candidate_relative = (
                f"jobs/{job.job_id}/candidates/candidate-{attempt:02d}.py"
            )
            _write_text_new(run_directory / candidate_relative, candidate)
        except GenerationError:
            candidate_hash = None
            candidate_relative = None
            extraction = "failed"
            status = GenerationStatus.MALFORMED

        reasoning_hash = None
        reasoning_relative = None
        if response.reasoning_content:
            reasoning_hash = hashlib.sha256(response.reasoning_content.encode()).hexdigest()
            reasoning_relative = (
                f"jobs/{job.job_id}/reasoning/reasoning-{attempt:02d}.txt"
            )
            _write_text_new(run_directory / reasoning_relative, response.reasoning_content)
        raw_relative = _response_path(Path("."), job, attempt).as_posix()
        record = GenerationRecord(
            job_id=job.job_id,
            task_id=job.task_id,
            condition=job.condition,
            assigned_policy=job.assigned_policy,
            sample_index=job.sample_index,
            seed=job.seed,
            model=manifest.provider.model,
            thinking=job.thinking,
            status=status,
            extraction=extraction,
            prompt_sha256=request_artifact.model_request.prompt_sha256,
            content_sha256=hashlib.sha256(response.content.encode()).hexdigest(),
            candidate_sha256=candidate_hash,
            reasoning_sha256=reasoning_hash,
            reasoning_characters=len(response.reasoning_content),
            provider_request_id=response.request_id,
            finish_reason=response.finish_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
                "reasoning_tokens": response.usage.reasoning_tokens,
            },
            successful_attempt=attempt,
            raw_response_path=raw_relative,
            candidate_path=candidate_relative,
            reasoning_path=reasoning_relative,
        )
        _write_json_new(result_path, record)
        counters[status.value] += 1

    completed = sum(counters.values()) + failed + skipped
    return RunSummary(
        run_id=manifest.run_id,
        total_jobs=len(manifest.jobs),
        generated=counters[GenerationStatus.GENERATED.value],
        truncated=counters[GenerationStatus.TRUNCATED.value],
        malformed=counters[GenerationStatus.MALFORMED.value],
        failed=failed,
        skipped_complete=skipped,
        pending=len(manifest.jobs) - completed,
    )


def extract_python_source(content: str) -> tuple[str, str]:
    stripped = content.strip()
    if not stripped:
        raise GenerationError("model returned empty content")
    fenced = re.fullmatch(r"```(?:python|py)?\s*\n(.*?)\n```", stripped, flags=re.DOTALL)
    if fenced:
        source = fenced.group(1).strip()
        if not source:
            raise GenerationError("model returned an empty code fence")
        return f"{source}\n", "single_code_fence"
    if "```" in stripped:
        raise GenerationError("model returned malformed or multiple Markdown fences")
    return f"{stripped}\n", "raw_text"


def _job_seed(
    base_seed: int, task_id: str, condition: Stage0Condition, sample_index: int
) -> int:
    pair_key = {
        Stage0Condition.RELEVANT_CLAUSE_ONLY_A: "relevant_clause_only",
        Stage0Condition.RELEVANT_CLAUSE_ONLY_B: "relevant_clause_only",
        Stage0Condition.FULL_DOCUMENT_A: "full_document",
        Stage0Condition.FULL_DOCUMENT_B: "full_document",
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A: "native_thinking_full_document",
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_B: "native_thinking_full_document",
    }.get(condition, condition.value)
    value = f"{base_seed}:{task_id}:{pair_key}:{sample_index}".encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:4], "big") % (2**31)


def _next_attempt(run_directory: Path, job: GenerationJob) -> int:
    job_directory = run_directory / f"jobs/{job.job_id}"
    numbers: list[int] = []
    for pattern in ("attempts/attempt-*.json", "responses/response-*.json"):
        for path in job_directory.glob(pattern):
            match = re.search(r"-(\d+)\.json$", path.name)
            if match:
                numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def _attempt_path(run_directory: Path, job: GenerationJob, attempt: int) -> Path:
    return run_directory / f"jobs/{job.job_id}/attempts/attempt-{attempt:02d}.json"


def _response_path(run_directory: Path, job: GenerationJob, attempt: int) -> Path:
    return run_directory / f"jobs/{job.job_id}/responses/response-{attempt:02d}.json"


def _load_request(path: Path) -> RequestArtifact:
    try:
        return RequestArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise GenerationError(f"could not load request artifact {path}: {error}") from error


def _write_json_new(path: Path, value: StrictModel) -> None:
    _write_text_new(path, f"{value.model_dump_json(indent=2)}\n")


def _write_text_new(path: Path, value: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise GenerationError(f"could not create immutable artifact {path}: {error}") from error


def _now() -> str:
    return datetime.now(UTC).isoformat()
