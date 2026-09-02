"""Minimal native DashScope SSE client for hosted Qwen generation."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any, Protocol

from pydantic import Field

from sable_ir.schema import AlibabaQwenConfig, StrictModel


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ModelRequest(StrictModel):
    job_id: str
    model: str
    prompt: str
    prompt_sha256: str
    enable_thinking: bool
    seed: int = Field(ge=0, le=2**31 - 1)
    temperature: float = Field(ge=0, lt=2)
    top_p: float = Field(gt=0, le=1)
    max_tokens: int = Field(ge=1)


class TokenUsage(StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0


class ProviderResponse(StrictModel):
    request_id: str
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


class DashScopeClient:
    def __init__(
        self,
        config: AlibabaQwenConfig,
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
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": request.prompt}],
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "enable_thinking": request.enable_thinking,
                "incremental_output": True,
                "seed": request.seed,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens,
            },
        }

    def generate(self, request: ModelRequest) -> ProviderResponse:
        body = json.dumps(
            self.build_payload(request), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-DashScope-SSE": "enable",
        }
        try:
            lines = self.transport.stream(
                self.endpoint,
                headers,
                body,
                self.config.request_timeout_seconds,
            )
            events = tuple(_parse_sse(lines))
        except urllib.error.HTTPError as error:
            detail = error.read(65_536).decode("utf-8", errors="replace")
            raise ProviderError(
                f"DashScope HTTP {error.code}: {detail}",
                retryable=error.code == 429 or error.code >= 500,
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ProviderError(f"DashScope connection failed: {error}", retryable=True) from error

        if not events:
            raise ProviderError("DashScope returned no SSE result events", retryable=True)
        return _combine_events(events)


def _parse_sse(lines: Iterable[bytes]) -> Iterable[dict[str, Any]]:
    data_lines: list[str] = []
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="strict").rstrip("\r\n")
        if not line:
            yield from _decode_event(data_lines)
            data_lines.clear()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    yield from _decode_event(data_lines)


def _decode_event(data_lines: list[str]) -> Iterable[dict[str, Any]]:
    if not data_lines:
        return
    payload = "\n".join(data_lines)
    if payload == "[DONE]":
        return
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ProviderError(f"DashScope returned malformed SSE JSON: {error}") from error
    if not isinstance(decoded, dict):
        raise ProviderError("DashScope SSE data must contain a JSON object")
    yield decoded


def _combine_events(events: tuple[dict[str, Any], ...]) -> ProviderResponse:
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    request_id = ""
    finish_reason: str | None = None
    usage_data: dict[str, Any] = {}

    for event in events:
        if event.get("code") or event.get("message") and "output" not in event:
            code = event.get("code", "unknown")
            message = event.get("message", "unknown provider error")
            raise ProviderError(f"DashScope error {code}: {message}")
        request_id = str(event.get("request_id", request_id))
        usage = event.get("usage")
        if isinstance(usage, dict):
            usage_data = usage
        output = event.get("output")
        if not isinstance(output, dict):
            continue
        choices = output.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        raw_finish = choice.get("finish_reason")
        if raw_finish not in {None, "null"}:
            finish_reason = str(raw_finish)
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content_parts.append(_message_text(message.get("content")))
        reasoning_parts.append(_message_text(message.get("reasoning_content")))

    details = usage_data.get("output_tokens_details", {})
    if not isinstance(details, dict):
        details = {}
    usage = TokenUsage(
        input_tokens=_integer(usage_data.get("input_tokens")),
        output_tokens=_integer(usage_data.get("output_tokens")),
        total_tokens=_integer(usage_data.get("total_tokens")),
        reasoning_tokens=_integer(details.get("reasoning_tokens")),
    )
    if not request_id:
        raise ProviderError("DashScope response omitted request_id")
    return ProviderResponse(
        request_id=request_id,
        content="".join(content_parts),
        reasoning_content="".join(reasoning_parts),
        finish_reason=finish_reason,
        usage=usage,
        raw_events=events,
    )


def _message_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
