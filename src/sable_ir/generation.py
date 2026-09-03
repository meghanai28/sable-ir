"""Preparation and resumable execution of the hosted Stage 0 generation matrix."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Protocol

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


Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


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


class ManualRetryAuthorization(StrictModel):
    source_manifest_sha256: Sha256
    job_id: str
    prior_attempt_path: str
    prior_attempt_sha256: Sha256
    prior_attempt_finished_at: str
    cooldown_seconds: Literal[0, 65]
    earliest_retry_at: str
    additional_attempts: Literal[1] = 1
    automatic_retry: Literal[False] = False
    reason: Literal["provider_rate_limit_429", "stream_timeout_600"]

    @model_validator(mode="after")
    def require_exact_cooldown_and_safe_path(self) -> ManualRetryAuthorization:
        path = PurePosixPath(self.prior_attempt_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("prior_attempt_path must be source-run-relative")
        try:
            finished_at = datetime.fromisoformat(self.prior_attempt_finished_at)
            earliest_retry_at = datetime.fromisoformat(self.earliest_retry_at)
        except ValueError as error:
            raise ValueError("retry timestamps must be ISO-8601") from error
        if finished_at.tzinfo is None or earliest_retry_at.tzinfo is None:
            raise ValueError("retry timestamps must include UTC offsets")
        if earliest_retry_at != finished_at + timedelta(seconds=self.cooldown_seconds):
            raise ValueError("earliest_retry_at must enforce the exact cooldown")
        return self


class DatasetRevision(StrictModel):
    source_manifest_sha256: Sha256
    g7_audit_path: str
    g7_audit_sha256: Sha256
    changed_task_ids: tuple[str, ...]
    invalidated_job_ids: tuple[str, ...]
    carry_forward_basis: Literal["exact_model_request_and_test_hashes"] = (
        "exact_model_request_and_test_hashes"
    )

    @model_validator(mode="after")
    def require_safe_audit_path_and_unique_ids(self) -> DatasetRevision:
        path = PurePosixPath(self.g7_audit_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("g7_audit_path must be repository-relative")
        if len(self.changed_task_ids) != len(set(self.changed_task_ids)):
            raise ValueError("changed_task_ids must be unique")
        if len(self.invalidated_job_ids) != len(set(self.invalidated_job_ids)):
            raise ValueError("invalidated_job_ids must be unique")
        return self


class GenerationManifest(StrictModel):
    schema_version: int = 10
    run_id: str
    created_at: str
    generation_harness_version: Literal[
        "stage0-kimi-generation-v2",
        "stage0-kimi-generation-v3",
        "stage0-kimi-generation-v4",
        "stage0-kimi-generation-v5",
        "stage0-kimi-generation-v6",
    ] = "stage0-kimi-generation-v6"
    evaluation_harness_version: Literal["stage0-evaluation-v2"] = "stage0-evaluation-v2"
    migrated_from_manifest_sha256: Sha256 | None = None
    carried_forward_result_sha256s: dict[str, Sha256] = Field(default_factory=dict)
    invalidated_source_result_sha256s: dict[str, Sha256] = Field(default_factory=dict)
    manual_retry_authorization: ManualRetryAuthorization | None = None
    dataset_revision: DatasetRevision | None = None
    execution_order: tuple[str, ...] | None = None
    config_sha256: str
    provider: KimiConfig
    sandbox: SandboxConfig
    thresholds: Stage0Thresholds
    jobs: tuple[GenerationJob, ...]

    @model_validator(mode="after")
    def require_consistent_recovery_lineage(self) -> GenerationManifest:
        job_ids = {job.job_id for job in self.jobs}
        carried_ids = set(self.carried_forward_result_sha256s)
        invalidated_ids = set(self.invalidated_source_result_sha256s)
        if not carried_ids <= job_ids:
            raise ValueError("carried-forward result references an unknown job")
        if not invalidated_ids <= job_ids:
            raise ValueError("invalidated source result references an unknown job")
        if carried_ids & invalidated_ids:
            raise ValueError("a source result cannot be both carried and invalidated")
        recovery_present = (
            bool(carried_ids)
            or bool(invalidated_ids)
            or self.manual_retry_authorization is not None
            or self.dataset_revision is not None
        )
        if recovery_present and self.migrated_from_manifest_sha256 is None:
            raise ValueError("recovery metadata requires a source manifest hash")
        authorization = self.manual_retry_authorization
        if authorization is not None:
            if authorization.source_manifest_sha256 != self.migrated_from_manifest_sha256:
                raise ValueError("retry authorization must reference the source manifest")
            if authorization.job_id not in job_ids:
                raise ValueError("retry authorization references an unknown job")
            if authorization.job_id in carried_ids:
                raise ValueError("a retry-authorized job cannot have a carried result")
        revision = self.dataset_revision
        if revision is not None:
            if revision.source_manifest_sha256 != self.migrated_from_manifest_sha256:
                raise ValueError("dataset revision must reference the source manifest")
            if set(revision.invalidated_job_ids) != invalidated_ids:
                raise ValueError("dataset revision must enumerate every invalidated result")
            if carried_ids | invalidated_ids != job_ids:
                raise ValueError("dataset revision must classify every source result")
            if authorization is not None:
                raise ValueError("dataset revision cannot also authorize a provider retry")
        elif invalidated_ids:
            raise ValueError("invalidated results require dataset revision metadata")
        if self.execution_order is not None:
            if len(self.execution_order) != len(set(self.execution_order)):
                raise ValueError("execution_order must not contain duplicate jobs")
            pending_source_ids = job_ids - carried_ids
            if set(self.execution_order) != pending_source_ids:
                raise ValueError("execution_order must enumerate every non-carried job")
        if self.schema_version >= 8 and self.provider.minimum_request_interval_seconds is None:
            raise ValueError("schema v8 manifests require an explicit request interval")
        return self


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
    schema_version: int = 2
    attempt: int
    started_at: str
    finished_at: str
    latency_seconds: float = Field(ge=0)
    succeeded: bool
    retryable: bool = False
    provider_request_id: str | None = None
    error: str | None = None
    automatic_retry: Literal[False] = False
    authorized_lineage_retry_of_attempt_sha256: Sha256 | None = None


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
    carried_forward_result_sha256s: dict[str, str] | None = None,
    manual_retry_authorization: ManualRetryAuthorization | None = None,
    invalidated_source_result_sha256s: dict[str, str] | None = None,
    dataset_revision: DatasetRevision | None = None,
    execution_order: tuple[str, ...] | None = None,
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
        carried_forward_result_sha256s=carried_forward_result_sha256s or {},
        invalidated_source_result_sha256s=(
            invalidated_source_result_sha256s or {}
        ),
        manual_retry_authorization=manual_retry_authorization,
        dataset_revision=dataset_revision,
        execution_order=execution_order,
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
        provider=config.hosted_kimi,
        sandbox=config.sandbox,
        thresholds=config.thresholds,
        jobs=tuple(jobs),
    )
    _write_json_new(run_directory / "manifest.json", manifest)
    return manifest


def prepare_stage0_recovery(
    config: Stage0Config,
    repository_root: Path,
    source_manifest_path: Path,
    run_directory: Path,
    run_id: str,
    retry_job_id: str,
    *,
    cooldown_seconds: int = 65,
    retry_reason: Literal["provider_rate_limit_429", "stream_timeout_600"] = (
        "provider_rate_limit_429"
    ),
    execution_order: tuple[str, ...] | None = None,
) -> GenerationManifest:
    """Create a new immutable run that carries valid results across one manual retry."""
    if retry_reason == "provider_rate_limit_429":
        if cooldown_seconds != 65:
            raise GenerationError("rate-limit recovery requires a 65-second cooldown")
        approved_cooldown: Literal[0, 65] = 65
    else:
        if cooldown_seconds != 0:
            raise GenerationError("stream-timeout recovery uses no additional cooldown")
        approved_cooldown = 0
    source_manifest_path = source_manifest_path.resolve()
    source_manifest = load_manifest(source_manifest_path)
    source_directory = source_manifest_path.parent
    source_bytes = source_manifest_path.read_bytes()
    source_manifest_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_manifest.provider.thinking_max_completion_tokens != 32_768:
        raise GenerationError("source recovery manifest does not use the approved 32K ceiling")
    provider_identity = (
        source_manifest.provider.provider,
        source_manifest.provider.transport,
        source_manifest.provider.model,
        source_manifest.provider.base_url,
        source_manifest.provider.generation_path,
        source_manifest.provider.api_key_env,
        source_manifest.provider.max_completion_tokens,
        source_manifest.provider.thinking_max_completion_tokens,
        source_manifest.provider.max_attempts,
        source_manifest.provider.automatic_retries,
    )
    requested_provider_identity = (
        config.hosted_kimi.provider,
        config.hosted_kimi.transport,
        config.hosted_kimi.model,
        config.hosted_kimi.base_url,
        config.hosted_kimi.generation_path,
        config.hosted_kimi.api_key_env,
        config.hosted_kimi.max_completion_tokens,
        config.hosted_kimi.thinking_max_completion_tokens,
        config.hosted_kimi.max_attempts,
        config.hosted_kimi.automatic_retries,
    )
    if provider_identity != requested_provider_identity:
        raise GenerationError("recovery would change a frozen provider request setting")
    if config.hosted_kimi.minimum_request_interval_seconds != 25.0:
        raise GenerationError("rate-limit recovery requires a 25-second request interval")
    if retry_reason == "stream_timeout_600" and (
        source_manifest.provider.max_stream_seconds != 600.0
        or config.hosted_kimi.max_stream_seconds != 900.0
    ):
        raise GenerationError("timeout recovery may change stream duration only from 600 to 900")

    source_jobs = {job.job_id: job for job in source_manifest.jobs}
    if retry_job_id not in source_jobs:
        raise GenerationError(f"source manifest does not contain retry job: {retry_job_id}")
    carried_hashes: dict[str, str] = {}
    carried_paths: set[str] = set()
    for job in source_manifest.jobs:
        result_path = _checked_optional_run_path(source_directory, job.result_path)
        if result_path is None:
            continue
        result_bytes = result_path.read_bytes()
        try:
            generation = GenerationRecord.model_validate_json(result_bytes)
        except ValidationError as error:
            raise GenerationError(
                f"could not validate carried result for {job.job_id}: {error}"
            ) from error
        _validate_carried_generation(generation, job, source_manifest)
        if generation.status is not GenerationStatus.GENERATED:
            raise GenerationError(f"only complete generated results may be carried: {job.job_id}")
        carried_hashes[job.job_id] = hashlib.sha256(result_bytes).hexdigest()
        carried_paths.add(job.result_path)

        attempt_relative = (
            f"jobs/{job.job_id}/attempts/attempt-{generation.successful_attempt:02d}.json"
        )
        attempt_path = _checked_required_run_path(
            source_directory, attempt_relative, "successful attempt"
        )
        try:
            attempt = AttemptRecord.model_validate_json(attempt_path.read_bytes())
        except ValidationError as error:
            raise GenerationError(
                f"could not validate carried attempt for {job.job_id}: {error}"
            ) from error
        if (
            not attempt.succeeded
            or attempt.provider_request_id != generation.provider_request_id
            or attempt.attempt != generation.successful_attempt
        ):
            raise GenerationError(f"carried attempt metadata mismatch for {job.job_id}")
        carried_paths.add(attempt_relative)

        raw_path = _checked_required_run_path(
            source_directory, generation.raw_response_path, "raw response"
        )
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != generation.raw_response_sha256:
            raise GenerationError(f"carried raw response hash mismatch for {job.job_id}")
        carried_paths.add(generation.raw_response_path)

        if generation.candidate_path is None or generation.candidate_sha256 is None:
            raise GenerationError(f"carried result is missing its candidate: {job.job_id}")
        candidate_path = _checked_required_run_path(
            source_directory, generation.candidate_path, "candidate"
        )
        if hashlib.sha256(candidate_path.read_bytes()).hexdigest() != generation.candidate_sha256:
            raise GenerationError(f"carried candidate hash mismatch for {job.job_id}")
        carried_paths.add(generation.candidate_path)

        if generation.reasoning_path is not None:
            if generation.reasoning_sha256 is None:
                raise GenerationError(f"carried reasoning hash is missing for {job.job_id}")
            reasoning_path = _checked_required_run_path(
                source_directory, generation.reasoning_path, "reasoning"
            )
            if (
                hashlib.sha256(reasoning_path.read_bytes()).hexdigest()
                != generation.reasoning_sha256
            ):
                raise GenerationError(f"carried reasoning hash mismatch for {job.job_id}")
            carried_paths.add(generation.reasoning_path)

    if retry_job_id in carried_hashes:
        raise GenerationError("retry job already has a completed result")
    failed_attempts = sorted(
        (source_directory / "jobs" / retry_job_id / "attempts").glob("attempt-*.json")
    )
    if len(failed_attempts) != 1:
        raise GenerationError("retry job must have exactly one preserved source attempt")
    failed_attempt_path = failed_attempts[0]
    failed_attempt_bytes = failed_attempt_path.read_bytes()
    try:
        failed_attempt = AttemptRecord.model_validate_json(failed_attempt_bytes)
    except ValidationError as error:
        raise GenerationError(f"could not validate preserved 429 attempt: {error}") from error
    if failed_attempt.succeeded or failed_attempt.error is None:
        raise GenerationError("manual retry authorization requires a failed source attempt")
    if retry_reason == "provider_rate_limit_429" and (
        not failed_attempt.retryable or "Kimi HTTP 429:" not in failed_attempt.error
    ):
        raise GenerationError("rate-limit retry authorization requires a retryable Kimi HTTP 429")
    if retry_reason == "stream_timeout_600" and (
        failed_attempt.error != "Kimi SSE response exceeded the configured wall-time limit"
        or failed_attempt.latency_seconds < 600.0
    ):
        raise GenerationError("timeout retry authorization requires the preserved 600s timeout")
    try:
        failed_finished_at = datetime.fromisoformat(failed_attempt.finished_at)
    except ValueError as error:
        raise GenerationError("failed attempt has an invalid completion timestamp") from error
    if failed_finished_at.tzinfo is None:
        raise GenerationError("failed attempt completion timestamp lacks a UTC offset")
    earliest_retry_at = failed_finished_at + timedelta(seconds=approved_cooldown)
    failed_attempt_relative = failed_attempt_path.relative_to(source_directory).as_posix()
    authorization = ManualRetryAuthorization(
        source_manifest_sha256=source_manifest_sha256,
        job_id=retry_job_id,
        prior_attempt_path=failed_attempt_relative,
        prior_attempt_sha256=hashlib.sha256(failed_attempt_bytes).hexdigest(),
        prior_attempt_finished_at=failed_attempt.finished_at,
        cooldown_seconds=approved_cooldown,
        earliest_retry_at=earliest_retry_at.isoformat(),
        additional_attempts=1,
        automatic_retry=False,
        reason=retry_reason,
    )
    manifest = prepare_stage0_run(
        config,
        repository_root,
        run_directory,
        run_id,
        migrated_from_manifest_sha256=source_manifest_sha256,
        carried_forward_result_sha256s=carried_hashes,
        manual_retry_authorization=authorization,
        execution_order=execution_order,
    )
    new_jobs = {job.job_id: job for job in manifest.jobs}
    if set(new_jobs) != set(source_jobs):
        raise GenerationError("recovery changed the frozen job matrix")
    for job_id, source_job in source_jobs.items():
        new_job = new_jobs[job_id]
        if (
            source_job.request_sha256 != new_job.request_sha256
            or source_job.condition != new_job.condition
            or source_job.assigned_policy != new_job.assigned_policy
            or source_job.pair_id != new_job.pair_id
        ):
            raise GenerationError(f"recovery changed the frozen request for {job_id}")
    destination_directory = run_directory.resolve()
    for relative in sorted(carried_paths):
        source = _checked_required_run_path(source_directory, relative, "carried artifact")
        _write_bytes_new(destination_directory / relative, source.read_bytes())
    return manifest


def prepare_stage0_dataset_revision(
    config: Stage0Config,
    repository_root: Path,
    source_manifest_path: Path,
    g7_audit_path: Path,
    run_directory: Path,
    run_id: str,
    changed_task_ids: tuple[str, ...],
) -> GenerationManifest:
    """Carry exact-input results while invalidating changed full-document prompts."""
    changed_tasks = set(changed_task_ids)
    if not changed_tasks:
        raise GenerationError("dataset revision requires at least one changed task")
    root = repository_root.resolve()
    source_manifest_path = source_manifest_path.resolve()
    source_manifest = load_manifest(source_manifest_path)
    source_directory = source_manifest_path.parent
    source_manifest_sha256 = hashlib.sha256(source_manifest_path.read_bytes()).hexdigest()
    source_task_ids = {job.task_id for job in source_manifest.jobs}
    if not changed_tasks <= source_task_ids:
        raise GenerationError("dataset revision names an unknown changed task")

    audit_path = g7_audit_path.resolve()
    try:
        audit_relative = audit_path.relative_to(root).as_posix()
        audit_bytes = audit_path.read_bytes()
        audit_data = json.loads(audit_bytes)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        raise GenerationError(f"could not load the revised G7 audit: {error}") from error
    if not isinstance(audit_data, dict):
        raise GenerationError("revised G7 audit must be a JSON object")
    if (
        audit_data.get("gate") != "G7"
        or audit_data.get("audit_complete") is not True
        or audit_data.get("g7_passed") is not True
        or audit_data.get("gate_status") != "passed"
    ):
        raise GenerationError("dataset revision requires a completed passing G7 audit")
    audited_hashes = audit_data.get("task_sha256")
    current_task_hashes = {
        load_task(root / relative).id: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in config.task_paths
    }
    if audited_hashes != current_task_hashes:
        raise GenerationError("revised G7 audit does not bind the current task files")
    audited_changes = {
        change.get("task_id")
        for change in audit_data.get("changes", [])
        if isinstance(change, dict)
    }
    if audited_changes != changed_tasks:
        raise GenerationError("revised G7 audit changed-task set does not match the request")

    full_document_conditions = {
        Stage0Condition.FULL_DOCUMENT_A,
        Stage0Condition.FULL_DOCUMENT_B,
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_A,
        Stage0Condition.NATIVE_THINKING_FULL_DOCUMENT_B,
    }
    carried_hashes: dict[str, str] = {}
    invalidated_hashes: dict[str, str] = {}
    carried_paths: set[str] = set()
    for job in source_manifest.jobs:
        generation, result_bytes, artifact_paths = _validated_completed_result(
            source_directory, job, source_manifest
        )
        del generation
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()
        if job.task_id in changed_tasks and job.condition in full_document_conditions:
            invalidated_hashes[job.job_id] = result_sha256
        else:
            carried_hashes[job.job_id] = result_sha256
            carried_paths.update(artifact_paths)

    revision = DatasetRevision(
        source_manifest_sha256=source_manifest_sha256,
        g7_audit_path=audit_relative,
        g7_audit_sha256=hashlib.sha256(audit_bytes).hexdigest(),
        changed_task_ids=tuple(sorted(changed_tasks)),
        invalidated_job_ids=tuple(sorted(invalidated_hashes)),
    )
    manifest = prepare_stage0_run(
        config,
        root,
        run_directory,
        run_id,
        source_manifest_sha256,
        carried_hashes,
        None,
        invalidated_hashes,
        revision,
    )
    source_jobs = {job.job_id: job for job in source_manifest.jobs}
    new_jobs = {job.job_id: job for job in manifest.jobs}
    if set(source_jobs) != set(new_jobs):
        raise GenerationError("dataset revision changed the frozen job matrix")
    for job_id, source_job in source_jobs.items():
        new_job = new_jobs[job_id]
        source_request = _load_request(source_directory / source_job.request_path)
        new_request = _load_request(run_directory.resolve() / new_job.request_path)
        stable_job_metadata = (
            source_job.task_id,
            source_job.task_path,
            source_job.upstream_source_revision,
            source_job.upstream_task_id,
            source_job.upstream_prompt_sha256,
            source_job.test_sha256s,
            source_job.condition,
            source_job.assigned_policy,
            source_job.sample_index,
            source_job.pair_id,
            source_job.thinking_requested,
        )
        new_stable_job_metadata = (
            new_job.task_id,
            new_job.task_path,
            new_job.upstream_source_revision,
            new_job.upstream_task_id,
            new_job.upstream_prompt_sha256,
            new_job.test_sha256s,
            new_job.condition,
            new_job.assigned_policy,
            new_job.sample_index,
            new_job.pair_id,
            new_job.thinking_requested,
        )
        if stable_job_metadata != new_stable_job_metadata:
            raise GenerationError(f"dataset revision changed stable inputs for {job_id}")
        if job_id in carried_hashes:
            if (
                source_request.model_request != new_request.model_request
                or source_request.task_prompt != new_request.task_prompt
            ):
                raise GenerationError(f"carried job prompt changed for {job_id}")
        elif (
            source_request.model_request.prompt_sha256
            == new_request.model_request.prompt_sha256
        ):
            raise GenerationError(f"invalidated full-document prompt did not change: {job_id}")

    destination_directory = run_directory.resolve()
    for relative in sorted(carried_paths):
        source = _checked_required_run_path(source_directory, relative, "carried artifact")
        _write_bytes_new(destination_directory / relative, source.read_bytes())
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
    selected = select_manifest_jobs(
        manifest, limit=limit, job_id=job_id, use_execution_order=True
    )
    counters = {status.value: 0 for status in GenerationStatus}
    failed = 0
    skipped = 0
    last_request_started: float | None = None

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
        retry_authorization = manifest.manual_retry_authorization
        retry_of_attempt_sha256 = None
        if retry_authorization is not None and job.job_id == retry_authorization.job_id:
            _enforce_retry_cooldown(retry_authorization)
            retry_of_attempt_sha256 = retry_authorization.prior_attempt_sha256
        request_interval = manifest.provider.minimum_request_interval_seconds or 0.0
        if last_request_started is not None:
            wait_seconds = request_interval - (time.monotonic() - last_request_started)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        started_at = _now()
        started = time.monotonic()
        last_request_started = started
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
                    automatic_retry=False,
                    authorized_lineage_retry_of_attempt_sha256=(
                        retry_of_attempt_sha256
                    ),
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
                automatic_retry=False,
                authorized_lineage_retry_of_attempt_sha256=retry_of_attempt_sha256,
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

    completed_results = sum(
        (run_directory / manifest_job.result_path).is_file()
        for manifest_job in manifest.jobs
    )
    return RunSummary(
        run_id=manifest.run_id,
        total_jobs=len(manifest.jobs),
        generated=counters[GenerationStatus.GENERATED.value],
        truncated=counters[GenerationStatus.TRUNCATED.value],
        malformed=counters[GenerationStatus.MALFORMED.value],
        failed=failed,
        skipped_complete=skipped,
        pending=len(manifest.jobs) - completed_results,
    )


def select_manifest_jobs(
    manifest: GenerationManifest,
    *,
    limit: int | None = None,
    job_id: str | None = None,
    use_execution_order: bool = False,
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
    if use_execution_order and manifest.execution_order is not None:
        jobs_by_id = {job.job_id: job for job in manifest.jobs}
        return [jobs_by_id[selected_id] for selected_id in manifest.execution_order]
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


def _validate_carried_generation(
    generation: GenerationRecord,
    job: GenerationJob,
    manifest: GenerationManifest,
) -> None:
    observed = (
        generation.job_id,
        generation.task_id,
        generation.condition,
        generation.assigned_policy,
        generation.sample_index,
        generation.pair_id,
        generation.provider_seed_supported,
        generation.provider_seed_sent,
        generation.model,
        generation.thinking_requested,
    )
    expected = (
        job.job_id,
        job.task_id,
        job.condition,
        job.assigned_policy,
        job.sample_index,
        job.pair_id,
        job.provider_seed_supported,
        job.provider_seed_sent,
        manifest.provider.model,
        job.thinking_requested,
    )
    if observed != expected:
        raise GenerationError(f"carried generation metadata mismatch for {job.job_id}")


def _validated_completed_result(
    source_directory: Path,
    job: GenerationJob,
    manifest: GenerationManifest,
) -> tuple[GenerationRecord, bytes, set[str]]:
    request_path = _checked_required_run_path(
        source_directory, job.request_path, "source request"
    )
    request_bytes = request_path.read_bytes()
    if hashlib.sha256(request_bytes).hexdigest() != job.request_sha256:
        raise GenerationError(f"source request hash mismatch for {job.job_id}")
    request = _load_request(request_path)
    _validate_request_metadata(request, job, manifest)

    result_path = _checked_required_run_path(
        source_directory, job.result_path, "source result"
    )
    result_bytes = result_path.read_bytes()
    try:
        generation = GenerationRecord.model_validate_json(result_bytes)
    except ValidationError as error:
        raise GenerationError(
            f"could not validate source result for {job.job_id}: {error}"
        ) from error
    _validate_carried_generation(generation, job, manifest)
    if generation.status is not GenerationStatus.GENERATED:
        raise GenerationError(f"source result is not a complete generation: {job.job_id}")

    paths = {job.result_path}
    attempt_relative = (
        f"jobs/{job.job_id}/attempts/attempt-{generation.successful_attempt:02d}.json"
    )
    attempt_path = _checked_required_run_path(
        source_directory, attempt_relative, "successful attempt"
    )
    try:
        attempt = AttemptRecord.model_validate_json(attempt_path.read_bytes())
    except ValidationError as error:
        raise GenerationError(
            f"could not validate source attempt for {job.job_id}: {error}"
        ) from error
    if (
        not attempt.succeeded
        or attempt.attempt != generation.successful_attempt
        or attempt.provider_request_id != generation.provider_request_id
    ):
        raise GenerationError(f"source attempt metadata mismatch for {job.job_id}")
    paths.add(attempt_relative)

    response_path = _checked_required_run_path(
        source_directory, generation.raw_response_path, "raw response"
    )
    response_bytes = response_path.read_bytes()
    if hashlib.sha256(response_bytes).hexdigest() != generation.raw_response_sha256:
        raise GenerationError(f"source response hash mismatch for {job.job_id}")
    try:
        response = ProviderResponse.model_validate_json(response_bytes)
    except ValidationError as error:
        raise GenerationError(
            f"could not validate source response for {job.job_id}: {error}"
        ) from error
    expected_usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
        "reasoning_tokens": response.usage.reasoning_tokens,
    }
    if (
        response.request_id != generation.provider_request_id
        or response.model != generation.model
        or response.finish_reason != generation.finish_reason
        or response.finish_reason == "length"
        or expected_usage != generation.usage
        or hashlib.sha256(response.content.encode()).hexdigest()
        != generation.content_sha256
    ):
        raise GenerationError(f"source response metadata mismatch for {job.job_id}")
    paths.add(generation.raw_response_path)

    if generation.candidate_path is None or generation.candidate_sha256 is None:
        raise GenerationError(f"source candidate metadata is missing for {job.job_id}")
    candidate_path = _checked_required_run_path(
        source_directory, generation.candidate_path, "candidate"
    )
    if hashlib.sha256(candidate_path.read_bytes()).hexdigest() != generation.candidate_sha256:
        raise GenerationError(f"source candidate hash mismatch for {job.job_id}")
    candidate, extraction = extract_python_source(response.content)
    if (
        hashlib.sha256(candidate.encode()).hexdigest() != generation.candidate_sha256
        or extraction != generation.extraction
    ):
        raise GenerationError(f"source candidate extraction mismatch for {job.job_id}")
    paths.add(generation.candidate_path)

    if generation.reasoning_content_present:
        if generation.reasoning_path is None or generation.reasoning_sha256 is None:
            raise GenerationError(f"source reasoning metadata is missing for {job.job_id}")
        reasoning_path = _checked_required_run_path(
            source_directory, generation.reasoning_path, "reasoning"
        )
        reasoning_bytes = reasoning_path.read_bytes()
        reasoning_sha256 = hashlib.sha256(response.reasoning_content.encode()).hexdigest()
        if (
            hashlib.sha256(reasoning_bytes).hexdigest() != reasoning_sha256
            or generation.reasoning_sha256 != reasoning_sha256
        ):
            raise GenerationError(f"source reasoning hash mismatch for {job.job_id}")
        paths.add(generation.reasoning_path)
    elif response.reasoning_content or generation.reasoning_path is not None:
        raise GenerationError(f"unexpected source reasoning artifact for {job.job_id}")
    return generation, result_bytes, paths


def _enforce_retry_cooldown(authorization: ManualRetryAuthorization) -> None:
    try:
        earliest_retry_at = datetime.fromisoformat(authorization.earliest_retry_at)
    except ValueError as error:
        raise GenerationError("manual retry authorization has an invalid timestamp") from error
    if datetime.now(UTC) < earliest_retry_at.astimezone(UTC):
        raise GenerationError(
            f"manual retry is locked until {authorization.earliest_retry_at}"
        )


def _checked_optional_run_path(root: Path, relative: str) -> Path | None:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise GenerationError(f"artifact path escapes source run: {relative}") from error
    if not path.exists():
        return None
    if not path.is_file():
        raise GenerationError(f"artifact path is not a file: {relative}")
    return path


def _checked_required_run_path(root: Path, relative: str, label: str) -> Path:
    path = _checked_optional_run_path(root, relative)
    if path is None:
        raise GenerationError(f"missing {label} artifact: {relative}")
    return path


def _write_json_new(path: Path, value: StrictModel) -> None:
    _write_text_new(path, f"{value.model_dump_json(indent=2)}\n")


def _write_bytes_new(path: Path, value: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise GenerationError(f"could not create immutable artifact {path}: {error}") from error


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
