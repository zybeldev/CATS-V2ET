from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .models import ExecutionContext


@dataclass(frozen=True)
class TEAReasoningOutput:
    action: Literal["SUBMIT_MARKET", "WAIT", "RECONCILE", "COMPLETE", "SUSPEND"]
    quantity: float | None = None
    rationale: str = ""


class TEAReasoningModel(Protocol):
    def decide(self, context: ExecutionContext) -> TEAReasoningOutput:
        ...


class DeterministicTEAReasoningModel:
    """Minimal capstone execution reasoning.

    TEA chooses execution mechanics but may not change PMA's target quantity.
    """

    def decide(self, context: ExecutionContext) -> TEAReasoningOutput:
        if context.remaining_quantity <= 0:
            return TEAReasoningOutput("COMPLETE", rationale="Target quantity already satisfied.")

        if context.certainty_status == "UNKNOWN_OUTCOME":
            return TEAReasoningOutput("RECONCILE", rationale="Broker outcome is uncertain.")

        if context.broker_order_id is None:
            return TEAReasoningOutput(
                "SUBMIT_MARKET",
                quantity=context.remaining_quantity,
                rationale="Submit remaining authorized quantity.",
            )

        return TEAReasoningOutput(
            "RECONCILE",
            rationale="Active broker order exists; reconcile with broker reality.",
	)
