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
        enable_thinking=thinking,
        pair_seed=7,
        max_completion_tokens=16_384 if thinking else 4096,
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
                "choices": [],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                    "completion_tokens_details": {"reasoning_tokens": 2},
                },
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
        "max_completion_tokens": 16_384,
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
