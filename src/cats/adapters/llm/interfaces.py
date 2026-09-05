from __future__ import annotations

from typing import Protocol


class StructuredReasoningModel(Protocol):
    """LLM boundary used by CATS agents.

    Implementations receive explicitly separated authoritative state, evidence,
    and deterministic measurements and return a structured dictionary.
    """

    def reason(self, *, task: str, context: dict) -> dict:
        ...
