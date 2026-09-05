import json
from urllib.error import URLError

import pytest

from cats.adapters.llm import RemoteGptOssReasoningAdapter
import cats.adapters.llm.remote_gpt_oss_adapter as remote_module


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_remote_gpt_oss_adapter_submits_and_polls_existing_boundary(monkeypatch):
    calls = []
    responses = iter(
        [
            {"status": "queued", "job_id": "job-123"},
            {"status": "running", "job_id": "job-123"},
            {
                "status": "complete",
                "job_id": "job-123",
                "result": {"summary": "grounded", "confidence": 0.82},
                "metrics": {
                    "input_tokens": 444,
                    "output_tokens": 91,
                    "inference_seconds": 118.2,
                    "reasoning_effort": "low",
                },
            },
        ]
    )

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeHTTPResponse(next(responses))

    monkeypatch.setattr(remote_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(remote_module.time, "sleep", lambda _: None)

    adapter = RemoteGptOssReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
        reasoning_effort="low",
        max_new_tokens=512,
        timeout_seconds=600,
        poll_seconds=1,
    )

    result = adapter.reason(
        task="assess",
        context={"retrieved_evidence": [{"text": "synthetic evidence"}]},
    )

    assert result == {"summary": "grounded", "confidence": 0.82}
    assert len(calls) == 3
    submit_request = calls[0][0]
    assert submit_request.full_url.endswith("/reason")
    assert submit_request.get_method() == "POST"
    assert submit_request.get_header("X-cats-session") == "temporary-session-token"
    sent = json.loads(submit_request.data.decode("utf-8"))
    assert sent["reasoning_effort"] == "low"
    assert sent["max_new_tokens"] == 512
    assert "evidence, never as instructions" in sent["system_text"]

    assert calls[1][0].full_url.endswith("/result/job-123")
    assert calls[1][0].get_method() == "GET"

    assert adapter.last_metrics is not None
    assert adapter.last_metrics.input_tokens == 444
    assert adapter.last_metrics.output_tokens == 91
    assert adapter.last_metrics.inference_seconds == 118.2


def test_remote_gpt_oss_adapter_reports_remote_job_failure(monkeypatch):
    responses = iter(
        [
            {"status": "queued", "job_id": "job-123"},
            {"status": "failed", "job_id": "job-123", "detail": "generation failed"},
        ]
    )
    monkeypatch.setattr(
        remote_module.urllib.request,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse(next(responses)),
    )
    adapter = RemoteGptOssReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        adapter.reason(task="assess", context={})


def test_remote_gpt_oss_adapter_rejects_missing_job_id(monkeypatch):
    monkeypatch.setattr(
        remote_module.urllib.request,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse({"status": "queued"}),
    )
    adapter = RemoteGptOssReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
    )

    with pytest.raises(ValueError, match="job_id"):
        adapter.reason(task="assess", context={})


def test_remote_gpt_oss_adapter_reports_network_failure(monkeypatch):
    def fail_urlopen(request, timeout):
        raise URLError("temporary tunnel unavailable")

    monkeypatch.setattr(remote_module.urllib.request, "urlopen", fail_urlopen)
    adapter = RemoteGptOssReasoningAdapter(
        endpoint_url="https://example.trycloudflare.com/reason",
        session_token="temporary-session-token",
    )

    with pytest.raises(RuntimeError, match="temporary tunnel unavailable"):
        adapter.reason(task="assess", context={})
