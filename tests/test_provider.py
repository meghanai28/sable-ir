from __future__ import annotations

import json
from collections.abc import Iterable

from sable_ir.provider import DashScopeClient, ModelRequest
from sable_ir.schema import AlibabaQwenConfig


class FakeStreamTransport:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines
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
        return (
            line
            for event in self.lines
            for line in event.splitlines(keepends=True)
        )


def _event(payload: dict[str, object]) -> bytes:
    return f"data:{json.dumps(payload)}\n\n".encode()


def test_native_sse_client_records_reasoning_content_and_usage() -> None:
    lines = [
        _event(
            {
                "request_id": "request-123",
                "output": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": [],
                                "reasoning_content": "consider ",
                            },
                            "finish_reason": "null",
                        }
                    ]
                },
                "usage": {"input_tokens": 20, "output_tokens": 2, "total_tokens": 22},
            }
        ),
        _event(
            {
                "request_id": "request-123",
                "output": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": [{"text": "def answer():\n"}],
                                "reasoning_content": "",
                            },
                            "finish_reason": "null",
                        }
                    ]
                },
                "usage": {"input_tokens": 20, "output_tokens": 5, "total_tokens": 25},
            }
        ),
        _event(
            {
                "request_id": "request-123",
                "output": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": [{"text": "    return 42\n"}],
                                "reasoning_content": "",
                            },
                            "finish_reason": "stop",
                        }
                    ]
                },
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "total_tokens": 30,
                    "output_tokens_details": {"reasoning_tokens": 2},
                },
            }
        ),
    ]
    transport = FakeStreamTransport(lines)
    config = AlibabaQwenConfig(api_key_env="DASHSCOPE_API_KEY")
    client = DashScopeClient(config, "sk-test-secret", transport)
    request = ModelRequest(
        job_id="job",
        model="qwen3.6-27b",
        prompt="write code",
        prompt_sha256="0" * 64,
        enable_thinking=True,
        seed=7,
        temperature=0.2,
        top_p=0.95,
        max_tokens=4096,
    )

    response = client.generate(request)

    assert response.content == "def answer():\n    return 42\n"
    assert response.reasoning_content == "consider "
    assert response.finish_reason == "stop"
    assert response.usage.reasoning_tokens == 2
    assert transport.url.endswith("/services/aigc/multimodal-generation/generation")
    assert transport.headers["X-DashScope-SSE"] == "enable"
    payload = json.loads(transport.body)
    assert payload["parameters"]["enable_thinking"] is True
    assert payload["parameters"]["incremental_output"] is True
    assert payload["input"]["messages"][0]["content"] == [{"text": "write code"}]
