from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
import urllib.error
import urllib.request

from .qwen_adapter import QwenReasoningAdapter


@dataclass(frozen=True)
class RemoteQwenReasoningMetrics:
    """Last-call observations for the Step 04C remote-Qwen experiment."""

    transport_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    inference_seconds: float | None
    thinking_enabled: bool


class RemoteQwenReasoningAdapter:
    """HTTP client implementing the existing CATS structured-reasoning boundary.

    The adapter keeps TAA local while delegating only Qwen inference to a remote
    GPU runtime such as Google Colab. The remote service receives one bounded
    task/context payload and returns one structured dictionary plus optional
    inference metrics.
    """

    def __init__(
        self,
        *,
        endpoint_url: str,
        session_token: str,
        enable_thinking: bool = False,
        max_new_tokens: int = 512,
        timeout_seconds: float = 120.0,
    ) -> None:
        endpoint_url = endpoint_url.strip()
        session_token = session_token.strip()
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must use http:// or https://")
        if not session_token:
            raise ValueError("session_token must not be empty")
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.endpoint_url = endpoint_url
        self.session_token = session_token
        self.enable_thinking = enable_thinking
        self.max_new_tokens = max_new_tokens
        self.timeout_seconds = timeout_seconds
        self.last_metrics: RemoteQwenReasoningMetrics | None = None

    def reason(self, *, task: str, context: dict) -> dict:
        payload = {
            "system_text": QwenReasoningAdapter.SYSTEM_TEXT,
            "task": task,
            "context": context,
            "enable_thinking": self.enable_thinking,
            "max_new_tokens": self.max_new_tokens,
        }
        request = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CATS-Session": self.session_token,
            },
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Remote Qwen endpoint returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Remote Qwen endpoint is unavailable: {exc.reason}") from exc
        transport_seconds = time.perf_counter() - started

        try:
            envelope = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("Remote Qwen endpoint did not return valid JSON.") from exc
        if not isinstance(envelope, dict):
            raise ValueError("Remote Qwen endpoint response must be one JSON object.")

        result = envelope.get("result")
        if not isinstance(result, dict):
            raise ValueError("Remote Qwen endpoint response must contain a result object.")

        metrics = envelope.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}
        self.last_metrics = RemoteQwenReasoningMetrics(
            transport_seconds=transport_seconds,
            input_tokens=self._optional_int(metrics.get("input_tokens")),
            output_tokens=self._optional_int(metrics.get("output_tokens")),
            inference_seconds=self._optional_float(metrics.get("inference_seconds")),
            thinking_enabled=bool(metrics.get("thinking_enabled", self.enable_thinking)),
        )
        return result

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return None if value is None else float(value)
