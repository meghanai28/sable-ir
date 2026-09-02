"""Preparation and resumable execution of the hosted Stage 0 generation matrix."""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

from pydantic import Field, ValidationError, model_validator

from sable_ir.config import load_task
from sable_ir.prompts import assigned_policy, build_task_prompt, build_wire_prompt, prompt_sha256
from sable_ir.provider import KimiClient, ModelRequest, ProviderError, ProviderResponse
from sable_ir.schema import (
    STAGE0_CONDITION_SPECS,
    KimiConfig,
    PolicyValue,
    SandboxConfig,
    Stage0Condition,
    Stage0Config,
    Stage0Thresholds,
    StrictModel,
    TestSuiteKind,
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
    job_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,159}$")
    task_id: str
    task_path: str
    task_sha256: str
    upstream_source_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    upstream_task_id: str
    upstream_prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    test_sha256s: dict[TestSuiteKind, str]
    condition: Stage0Condition
    assigned_policy: PolicyValue | None
    sample_index: int = Field(ge=0)
    pair_id: str | None = Field(
        default=None,
        pattern=(
            r"^[a-z][a-z0-9_]*__(?:relevant_clause_only|full_document|"
            r"native_thinking_full_document)__pair_[0-9]{2}$"
        ),
    )
    provider_seed_supported: Literal[False] = False
    provider_seed_sent: None = None
    thinking_requested: Literal["enabled", "disabled"]
    request_path: str
    request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_path: str

    @model_validator(mode="after")
    def require_safe_artifact_paths(self) -> GenerationJob:
        for label, value in (
            ("request_path", self.request_path),
            ("result_path", self.result_path),
        ):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"{label} must be a safe run-relative path")
        if self.pair_id != _pair_id(self.task_id, self.condition, self.sample_index):
            raise ValueError("pair_id does not identify the exact A/B condition pair")
        expected_thinking = (
            "enabled" if STAGE0_CONDITION_SPECS[self.condition].thinking else "disabled"
        )
        if self.thinking_requested != expected_thinking:
            raise ValueError("thinking_requested does not match the Stage 0 condition")
        return self


class GenerationManifest(StrictModel):
    schema_version: int = 6
    run_id: str
    created_at: str
    generation_harness_version: Literal["stage0-kimi-generation-v2"] = (
        "stage0-kimi-generation-v2"
    )
    evaluation_harness_version: Literal["stage0-evaluation-v2"] = "stage0-evaluation-v2"
    migrated_from_manifest_sha256: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )
    config_sha256: str
    provider: KimiConfig
    sandbox: SandboxConfig
    thresholds: Stage0Thresholds
    jobs: tuple[GenerationJob, ...]


class RequestArtifact(StrictModel):
    schema_version: int = 1
    task_id: str
    task_path: str
    task_sha256: str
    upstream_source_revision: str
    upstream_task_id: str
    upstream_prompt_sha256: str
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
    schema_version: int = 3
    job_id: str
    task_id: str
    condition: Stage0Condition
    assigned_policy: PolicyValue | None
    sample_index: int
    pair_id: str | None
    provider_seed_supported: Literal[False] = False
    provider_seed_sent: None = None
    model: str
    thinking_requested: Literal["enabled", "disabled"]
    reasoning_content_present: bool
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
    raw_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_path: str | None
    reasoning_path: str | None

    @model_validator(mode="after")
    def require_explicit_pairing_and_reasoning_metadata(self) -> GenerationRecord:
        paired = self.condition not in {
            Stage0Condition.ORIGINAL_BENCHMARK,
            Stage0Condition.SURFACE_ONLY_DIRECT,
        }
        if paired != (self.pair_id is not None):
            raise ValueError("only A/B generation records may have a pair_id")
        if self.reasoning_content_present != (self.reasoning_characters > 0):
            raise ValueError("reasoning_content_present must match reasoning_characters")
        if self.reasoning_content_present != (self.reasoning_sha256 is not None):
            raise ValueError("reasoning_content_present must match reasoning_sha256")
        return self


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


def provider_preflight(config: KimiConfig) -> ProviderPreflight:
    value = os.environ.get(config.api_key_env, "")
    present = bool(value.strip())
    looks_valid = present and value.startswith("sk-") and len(value) > 8
    ready = present and looks_valid
    note = (
        "Credential is present; this check does not contact Kimi or verify account access."
        if ready
        else f"Set a newly rotated {config.api_key_env} in the current shell."
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


def client_from_environment(config: KimiConfig) -> KimiClient:
    preflight = provider_preflight(config)
    if not preflight.ready_for_requests:
        raise GenerationError(preflight.note)
    return KimiClient(config, os.environ[config.api_key_env])


def prepare_stage0_run(
    config: Stage0Config,
    repository_root: Path,
    run_directory: Path,
    run_id: str,
    migrated_from_manifest_sha256: str | None = None,
) -> GenerationManifest:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", run_id):
        raise GenerationError("run_id must be 1-80 safe filename characters")
    if migrated_from_manifest_sha256 is not None and not re.fullmatch(
        r"[a-f0-9]{64}", migrated_from_manifest_sha256
    ):
        raise GenerationError("migrated_from_manifest_sha256 must be a SHA-256 digest")
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
            test_hashes = {
                kind: hashlib.sha256((root / suite.path).read_bytes()).hexdigest()
                for kind, suite in task.test_suites_for(condition).items()
            }
            for sample_index in range(config.samples_per_condition):
                job_id = f"{task.id}__{condition.value}__s{sample_index:02d}"
                job_root = f"jobs/{job_id}"
                pair_id = _pair_id(task.id, condition, sample_index)
                wire_prompt = build_wire_prompt(task, condition)
                max_completion_tokens = (
                    config.hosted_kimi.thinking_max_completion_tokens
                    if spec.thinking
                    else config.hosted_kimi.max_completion_tokens
                )
                model_request = ModelRequest(
                    job_id=job_id,
                    model=config.hosted_kimi.model,
                    prompt=wire_prompt,
                    prompt_sha256=prompt_sha256(wire_prompt),
                    thinking_requested="enabled" if spec.thinking else "disabled",
                    pair_id=pair_id,
                    provider_seed_supported=False,
                    provider_seed_sent=None,
                    max_completion_tokens=max_completion_tokens,
                )
                request_artifact = RequestArtifact(
                    task_id=task.id,
                    task_path=task_relative,
                    task_sha256=task_hash,
                    upstream_source_revision=task.provenance.source_revision,
                    upstream_task_id=task.original_benchmark.upstream_task_id,
                    upstream_prompt_sha256=task.original_benchmark.code_prompt_sha256,
                    condition=condition,
                    assigned_policy=assigned_policy(condition),
                    sample_index=sample_index,
                    task_prompt=build_task_prompt(task, condition),
                    model_request=model_request,
                )
                request_path = f"{job_root}/request.json"
                request_destination = run_directory / request_path
                _write_json_new(request_destination, request_artifact)
                request_hash = hashlib.sha256(request_destination.read_bytes()).hexdigest()
                jobs.append(
                    GenerationJob(
                        job_id=job_id,
                        task_id=task.id,
                        task_path=task_relative,
                        task_sha256=task_hash,
                        upstream_source_revision=task.provenance.source_revision,
                        upstream_task_id=task.original_benchmark.upstream_task_id,
                        upstream_prompt_sha256=task.original_benchmark.code_prompt_sha256,
                        test_sha256s=test_hashes,
                        condition=condition,
                        assigned_policy=assigned_policy(condition),
                        sample_index=sample_index,
                        pair_id=pair_id,
                        provider_seed_supported=False,
                        provider_seed_sent=None,
                        thinking_requested="enabled" if spec.thinking else "disabled",
                        request_path=request_path,
                        request_sha256=request_hash,
                        result_path=f"{job_root}/result.json",
                    )
                )

    config_json = config.model_dump_json(exclude={"artifacts_dir"})
    manifest = GenerationManifest(
        run_id=run_id,
        created_at=_now(),
        migrated_from_manifest_sha256=migrated_from_manifest_sha256,
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
        provider=config.hosted_kimi,
        sandbox=config.sandbox,
        thresholds=config.thresholds,
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
    job_id: str | None = None,
) -> RunSummary:
    manifest = load_manifest(manifest_path)
    run_directory = manifest_path.resolve().parent
    selected = select_manifest_jobs(manifest, limit=limit, job_id=job_id)
    counters = {status.value: 0 for status in GenerationStatus}
    failed = 0
    skipped = 0

    for job in selected:
        result_path = run_directory / job.result_path
        request_path = run_directory / job.request_path
        try:
            request_bytes = request_path.read_bytes()
        except OSError as error:
            raise GenerationError(
                f"could not read request artifact {request_path}: {error}"
            ) from error
        if hashlib.sha256(request_bytes).hexdigest() != job.request_sha256:
            raise GenerationError(f"request changed after preparation: {job.request_path}")
        request_artifact = _load_request(request_path)
        _validate_request_metadata(request_artifact, job, manifest)
        if result_path.exists():
            skipped += 1
            continue
        attempt = _next_attempt(run_directory, job)
        if attempt > manifest.provider.max_attempts:
            raise GenerationError(
                f"{job.job_id} already used its single provider attempt; prepare a new run "
                "only after inspecting the recorded failure"
            )
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
            failed += 1
            # Circuit breaker: never spend on later jobs after any provider failure.
            break
        if response.model != manifest.provider.model:
            raise GenerationError(
                f"provider returned {response.model}, expected {manifest.provider.model}"
            )
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
        raw_response_hash = hashlib.sha256(
            (run_directory / raw_relative).read_bytes()
        ).hexdigest()
        record = GenerationRecord(
            job_id=job.job_id,
            task_id=job.task_id,
            condition=job.condition,
            assigned_policy=job.assigned_policy,
            sample_index=job.sample_index,
            pair_id=job.pair_id,
            provider_seed_supported=job.provider_seed_supported,
            provider_seed_sent=job.provider_seed_sent,
            model=manifest.provider.model,
            thinking_requested=job.thinking_requested,
            reasoning_content_present=bool(response.reasoning_content),
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
            raw_response_sha256=raw_response_hash,
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


def select_manifest_jobs(
    manifest: GenerationManifest,
    *,
    limit: int | None = None,
    job_id: str | None = None,
) -> list[GenerationJob]:
    if limit is not None and job_id is not None:
        raise GenerationError("--limit and --job-id cannot be used together")
    if limit is not None:
        if limit < 1:
            raise GenerationError("--limit must be at least 1")
        return list(manifest.jobs[:limit])
    if job_id is not None:
        selected = [job for job in manifest.jobs if job.job_id == job_id]
        if not selected:
            raise GenerationError(f"manifest does not contain job: {job_id}")
        return selected
    return list(manifest.jobs)


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


def _pair_id(
    task_id: str, condition: Stage0Condition, sample_index: int
) -> str | None:
    if condition in {
        Stage0Condition.ORIGINAL_BENCHMARK,
        Stage0Condition.SURFACE_ONLY_DIRECT,
    }:
        return None
    pair_kind = {
        Stage0Condition.RELEVANT_CLAUSE_ONLY_A: "relevant_clause_only",
        Stage0Condition.RELEVANT_CLAUSE_ONLY_B: "relevant_clause_only",
        Stage0Condition.FULL_DOCUMENT_A: "full_document",
        Stage0Condition.FULL_DOCUMENT_B: "full_document",
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A: (
            "native_thinking_full_document"
        ),
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_B: (
            "native_thinking_full_document"
        ),
    }[condition]
    return f"{task_id}__{pair_kind}__pair_{sample_index:02d}"


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


def _validate_request_metadata(
    request: RequestArtifact,
    job: GenerationJob,
    manifest: GenerationManifest,
) -> None:
    observed = (
        request.task_id,
        request.task_path,
        request.task_sha256,
        request.upstream_source_revision,
        request.upstream_task_id,
        request.upstream_prompt_sha256,
        request.condition,
        request.assigned_policy,
        request.sample_index,
        request.model_request.job_id,
        request.model_request.model,
        request.model_request.thinking_requested,
        request.model_request.pair_id,
        request.model_request.provider_seed_supported,
        request.model_request.provider_seed_sent,
        request.model_request.max_completion_tokens,
    )
    expected = (
        job.task_id,
        job.task_path,
        job.task_sha256,
        job.upstream_source_revision,
        job.upstream_task_id,
        job.upstream_prompt_sha256,
        job.condition,
        job.assigned_policy,
        job.sample_index,
        job.job_id,
        manifest.provider.model,
        job.thinking_requested,
        job.pair_id,
        job.provider_seed_supported,
        job.provider_seed_sent,
        (
            manifest.provider.thinking_max_completion_tokens
            if job.thinking_requested == "enabled"
            else manifest.provider.max_completion_tokens
        ),
    )
    if observed != expected:
        raise GenerationError(f"request metadata mismatch for {job.job_id}")


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
