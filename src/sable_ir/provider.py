"""Minimal official Kimi OpenAI-compatible SSE client for hosted Stage 0 generation."""

from __future__ import annotations

import hashlib
import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any, Literal, Protocol

from pydantic import Field, model_validator

from sable_ir.schema import KimiConfig, StrictModel


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ModelRequest(StrictModel):
    job_id: str
    model: str
    prompt: str
    prompt_sha256: str
    thinking_requested: Literal["enabled", "disabled"]
    pair_id: str | None = Field(
        default=None,
        pattern=(
            r"^[a-z][a-z0-9_]*__(?:relevant_clause_only|full_document|"
            r"native_thinking_full_document)__pair_[0-9]{2}$"
        ),
    )
    provider_seed_supported: Literal[False] = False
    provider_seed_sent: None = None
    max_completion_tokens: int = Field(ge=1)

    @model_validator(mode="after")
    def require_matching_prompt_hash(self) -> ModelRequest:
        observed = hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()
        if self.prompt_sha256 != observed:
            raise ValueError("prompt_sha256 does not match prompt")
        return self


class TokenUsage(StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0


class ProviderResponse(StrictModel):
    request_id: str
    model: str
    content: str
    reasoning_content: str
    finish_reason: str | None
    usage: TokenUsage
    raw_events: tuple[dict[str, Any], ...]


class StreamTransport(Protocol):
    def stream(
        self,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> Iterable[bytes]: ...


class UrllibStreamTransport:
    def stream(
        self,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> Iterable[bytes]:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            yield from response


class KimiClient:
    def __init__(
        self,
        config: KimiConfig,
        api_key: str,
        transport: StreamTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ProviderError(f"{config.api_key_env} is empty")
        self.config = config
        self.api_key = api_key
        self.transport = transport or UrllibStreamTransport()

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}{self.config.generation_path}"

    def build_payload(self, request: ModelRequest) -> dict[str, Any]:
        return {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "thinking": {"type": request.thinking_requested},
            "max_completion_tokens": request.max_completion_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

    def generate(self, request: ModelRequest) -> ProviderResponse:
        body = json.dumps(
            self.build_payload(request), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        try:
            lines = self.transport.stream(
                self.endpoint,
                headers,
                body,
                self.config.request_timeout_seconds,
            )
            events, completed = _parse_sse(
                lines,
                max_bytes=self.config.max_response_bytes,
                max_events=self.config.max_sse_events,
                max_seconds=self.config.max_stream_seconds,
            )
        except urllib.error.HTTPError as error:
            detail = error.read(65_536).decode("utf-8", errors="replace")
            raise ProviderError(
                f"Kimi HTTP {error.code}: {_redact_secret(detail, self.api_key)}",
                retryable=error.code == 429 or error.code >= 500,
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as error:
            detail = _redact_secret(str(error), self.api_key)
            raise ProviderError(f"Kimi connection failed: {detail}", retryable=True) from error
        except UnicodeError as error:
            raise ProviderError(
                "Kimi returned text that was not valid UTF-8", retryable=True
            ) from error

        if not completed:
            raise ProviderError(
                "Kimi SSE stream ended before data: [DONE]", retryable=True
            )
        if not events:
            raise ProviderError("Kimi returned no SSE result events", retryable=True)
        return _combine_events(events, expected_model=request.model)


def _parse_sse(
    lines: Iterable[bytes],
    *,
    max_bytes: int,
    max_events: int,
    max_seconds: float,
) -> tuple[tuple[dict[str, Any], ...], bool]:
    data_lines: list[str] = []
    events: list[dict[str, Any]] = []
    completed = False
    received_bytes = 0
    started = time.monotonic()
    for raw_line in lines:
        received_bytes += len(raw_line)
        if received_bytes > max_bytes:
            raise ProviderError("Kimi SSE response exceeded the configured byte limit")
        if time.monotonic() - started > max_seconds:
            raise ProviderError("Kimi SSE response exceeded the configured wall-time limit")
        line = raw_line.decode("utf-8", errors="strict").rstrip("\r\n")
        if not line:
            event, done = _decode_event(data_lines)
            data_lines.clear()
            if event is not None:
                events.append(event)
                if len(events) > max_events:
                    raise ProviderError("Kimi SSE response exceeded the configured event limit")
            if done:
                completed = True
                break
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if not completed:
        event, done = _decode_event(data_lines)
        if event is not None:
            events.append(event)
            if len(events) > max_events:
                raise ProviderError("Kimi SSE response exceeded the configured event limit")
        completed = done
    return tuple(events), completed


def _decode_event(data_lines: list[str]) -> tuple[dict[str, Any] | None, bool]:
    if not data_lines:
        return None, False
    payload = "\n".join(data_lines)
    if payload == "[DONE]":
        return None, True
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ProviderError(f"Kimi returned malformed SSE JSON: {error}") from error
    if not isinstance(decoded, dict):
        raise ProviderError("Kimi SSE data must contain a JSON object")
    return decoded, False


def _combine_events(
    events: tuple[dict[str, Any], ...], *, expected_model: str
) -> ProviderResponse:
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    request_id = ""
    response_model = ""
    finish_reason: str | None = None
    usage_data: dict[str, Any] = {}
    usage_seen = False

    for event in events:
        error = event.get("error")
        if isinstance(error, dict):
            error_type = error.get("type", "unknown")
            message = error.get("message", "unknown provider error")
            raise ProviderError(f"Kimi error {error_type}: {message}")
        request_id = str(event.get("id", request_id))
        event_model = event.get("model")
        if isinstance(event_model, str):
            response_model = event_model
        usage = event.get("usage")
        if isinstance(usage, dict):
            usage_data = usage
            usage_seen = True
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        choice_usage = choice.get("usage")
        if isinstance(choice_usage, dict):
            usage_data = choice_usage
            usage_seen = True
        raw_finish = choice.get("finish_reason")
        if raw_finish not in {None, "null"}:
            finish_reason = str(raw_finish)
        message = choice.get("delta")
        if not isinstance(message, dict):
            message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content_parts.append(_message_text(message.get("content")))
        reasoning_parts.append(_message_text(message.get("reasoning_content")))

    if not request_id:
        raise ProviderError("Kimi response omitted completion id")
    if response_model != expected_model:
        raise ProviderError(
            f"Kimi returned model {response_model or '<missing>'}, expected {expected_model}"
        )
    if not usage_seen:
        raise ProviderError("Kimi response omitted final token usage")
    details = usage_data.get("completion_tokens_details", {})
    if not isinstance(details, dict):
        details = {}
    usage = TokenUsage(
        input_tokens=_integer(usage_data.get("prompt_tokens")),
        output_tokens=_integer(usage_data.get("completion_tokens")),
        total_tokens=_integer(usage_data.get("total_tokens")),
        reasoning_tokens=_integer(details.get("reasoning_tokens")),
    )
    return ProviderResponse(
        request_id=request_id,
        model=response_model,
        content="".join(content_parts),
        reasoning_content="".join(reasoning_parts),
        finish_reason=finish_reason,
        usage=usage,
        raw_events=events,
    )


def _message_text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _redact_secret(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value
