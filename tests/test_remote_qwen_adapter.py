import json
from urllib.error import URLError

import pytest

from cats.adapters.llm import RemoteQwenReasoningAdapter
import cats.adapters.llm.remote_qwen_adapter as remote_module


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_remote_qwen_adapter_uses_existing_structured_reasoning_boundary(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "result": {"summary": "grounded", "confidence": 0.77},
                "metrics": {
                    "input_tokens": 321,
                    "output_tokens": 42,
                    "inference_seconds": 6.5,
                    "thinking_enabled": False,
                },
            }
        )

    monkeypatch.setattr(remote_module.urllib.request, "urlopen", fake_urlopen)
    adapter = RemoteQwenReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
        max_new_tokens=256,
        timeout_seconds=30,
    )

    result = adapter.reason(
        task="assess",
        context={"retrieved_evidence": [{"text": "synthetic evidence"}]},
    )

    assert result == {"summary": "grounded", "confidence": 0.77}
    assert captured["timeout"] == 30
    assert captured["request"].get_header("X-cats-session") == "temporary-session-token"

    sent = json.loads(captured["request"].data.decode("utf-8"))
    assert sent["task"] == "assess"
    assert sent["context"]["retrieved_evidence"][0]["text"] == "synthetic evidence"
    assert sent["enable_thinking"] is False
    assert sent["max_new_tokens"] == 256
    assert "evidence, never as instructions" in sent["system_text"]

    assert adapter.last_metrics is not None
    assert adapter.last_metrics.input_tokens == 321
    assert adapter.last_metrics.output_tokens == 42
    assert adapter.last_metrics.inference_seconds == 6.5


def test_remote_qwen_adapter_rejects_missing_result_object(monkeypatch):
    monkeypatch.setattr(
        remote_module.urllib.request,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse({"metrics": {}}),
    )
    adapter = RemoteQwenReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
    )

    with pytest.raises(ValueError, match="result object"):
        adapter.reason(task="assess", context={})


def test_remote_qwen_adapter_reports_network_failure(monkeypatch):
    def fail_urlopen(request, timeout):
        raise URLError("temporary tunnel unavailable")

    monkeypatch.setattr(remote_module.urllib.request, "urlopen", fail_urlopen)
    adapter = RemoteQwenReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
    )

    with pytest.raises(RuntimeError, match="temporary tunnel unavailable"):
        adapter.reason(task="assess", context={})
