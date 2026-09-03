from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import pytest

from sable_ir.provider import KimiClient, ModelRequest, ProviderError
from sable_ir.schema import KimiConfig


class FakeStreamTransport:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.url = ""
        self.headers: dict[str, str] = {}
        self.body = b""
        self.timeout = 0.0

    def stream(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> Iterable[bytes]:
        self.url = url
        self.headers = headers
        self.body = body
        self.timeout = timeout
        return (line for chunk in self.chunks for line in chunk.splitlines(keepends=True))


class FailingStreamTransport(FakeStreamTransport):
    def stream(
        self, url: str, headers: dict[str, str], body: bytes, timeout: float
    ) -> Iterable[bytes]:
        del url, headers, body, timeout
        raise OSError("transport accidentally included sk-test-secret")


def _event(payload: dict[str, object]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


def _done() -> bytes:
    return b"data: [DONE]\n\n"


def _request(*, thinking: bool = True) -> ModelRequest:
    return ModelRequest(
        job_id="job",
        model="kimi-k2.6",
        prompt="write code",
        prompt_sha256=hashlib.sha256(b"write code").hexdigest(),
        thinking_requested="enabled" if thinking else "disabled",
        pair_id="example__full_document__pair_00",
        provider_seed_supported=False,
        provider_seed_sent=None,
        max_completion_tokens=32_768 if thinking else 4096,
    )


def test_kimi_sse_client_records_reasoning_content_usage_and_safe_payload() -> None:
    chunks = [
        _event(
            {
                "id": "completion-123",
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "delta": {"reasoning_content": "consider ", "content": ""},
                        "finish_reason": None,
                    }
                ],
            }
        ),
        _event(
            {
                "id": "completion-123",
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "delta": {"content": "def answer():\n    return 42\n"},
                        "finish_reason": "stop",
                    }
                ],
            }
        ),
        _event(
            {
                "id": "completion-123",
                "model": "kimi-k2.6",
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "stop",
                        "usage": {
                            "prompt_tokens": 20,
                            "completion_tokens": 10,
                            "total_tokens": 30,
                            "completion_tokens_details": {"reasoning_tokens": 2},
                        },
                    }
                ],
            }
        ),
        _done(),
    ]
    transport = FakeStreamTransport(chunks)
    config = KimiConfig(api_key_env="MOONSHOT_API_KEY")
    client = KimiClient(config, "sk-test-secret", transport)

    response = client.generate(_request())

    assert response.model == "kimi-k2.6"
    assert response.content == "def answer():\n    return 42\n"
    assert response.reasoning_content == "consider "
    assert response.finish_reason == "stop"
    assert response.usage.reasoning_tokens == 2
    assert transport.url == "https://api.moonshot.ai/v1/chat/completions"
    assert "Authorization" in transport.headers
    payload = json.loads(transport.body)
    assert payload == {
        "model": "kimi-k2.6",
        "messages": [{"role": "user", "content": "write code"}],
        "thinking": {"type": "enabled"},
        "max_completion_tokens": 32_768,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    assert "temperature" not in payload
    assert "top_p" not in payload
    assert "seed" not in payload


def test_nonthinking_payload_explicitly_disables_thinking() -> None:
    client = KimiClient(KimiConfig(api_key_env="MOONSHOT_API_KEY"), "sk-test-secret")

    payload = client.build_payload(_request(thinking=False))

    assert payload["thinking"] == {"type": "disabled"}
    assert payload["max_completion_tokens"] == 4096


def test_incomplete_sse_stream_is_retryable_but_not_accepted() -> None:
    transport = FakeStreamTransport(
        [
            _event(
                {
                    "id": "completion-123",
                    "model": "kimi-k2.6",
                    "choices": [
                        {"delta": {"content": "partial"}, "finish_reason": "stop"}
                    ],
                }
            )
        ]
    )
    client = KimiClient(
        KimiConfig(api_key_env="MOONSHOT_API_KEY"), "sk-test-secret", transport
    )

    with pytest.raises(ProviderError, match=r"data: \[DONE\]") as captured:
        client.generate(_request(thinking=False))

    assert captured.value.retryable


def test_wrong_returned_model_is_rejected() -> None:
    transport = FakeStreamTransport(
        [
            _event(
                {
                    "id": "completion-123",
                    "model": "another-model",
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                }
            ),
            _done(),
        ]
    )
    client = KimiClient(
        KimiConfig(api_key_env="MOONSHOT_API_KEY"), "sk-test-secret", transport
    )

    with pytest.raises(ProviderError, match="expected kimi-k2.6"):
        client.generate(_request(thinking=False))


def test_invalid_sse_utf8_is_a_retryable_provider_error() -> None:
    transport = FakeStreamTransport([b"data: \xff\n\n"])
    client = KimiClient(
        KimiConfig(api_key_env="MOONSHOT_API_KEY"), "sk-test-secret", transport
    )

    with pytest.raises(ProviderError, match="valid UTF-8") as captured:
        client.generate(_request(thinking=False))

    assert captured.value.retryable


def test_sse_event_limit_closes_a_runaway_stream() -> None:
    transport = FakeStreamTransport(
        [
            _event({"id": "completion-123", "model": "kimi-k2.6", "choices": []}),
            _event({"id": "completion-123", "model": "kimi-k2.6", "choices": []}),
        ]
    )
    config = KimiConfig(api_key_env="MOONSHOT_API_KEY", max_sse_events=1)
    client = KimiClient(config, "sk-test-secret", transport)

    with pytest.raises(ProviderError, match="configured event limit"):
        client.generate(_request(thinking=False))


def test_sse_wall_time_limit_closes_a_runaway_stream(monkeypatch) -> None:
    transport = FakeStreamTransport(
        [_event({"id": "completion-123", "model": "kimi-k2.6", "choices": []})]
    )
    clock = iter((0.0, 601.0))
    monkeypatch.setattr("sable_ir.provider.time.monotonic", lambda: next(clock))
    client = KimiClient(
        KimiConfig(api_key_env="MOONSHOT_API_KEY"), "sk-test-secret", transport
    )

    with pytest.raises(ProviderError, match="configured wall-time limit"):
        client.generate(_request(thinking=False))


def test_transport_errors_redact_the_api_key() -> None:
    client = KimiClient(
        KimiConfig(api_key_env="MOONSHOT_API_KEY"),
        "sk-test-secret",
        FailingStreamTransport([]),
    )

    with pytest.raises(ProviderError) as captured:
        client.generate(_request(thinking=False))

    assert "sk-test-secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
