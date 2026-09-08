from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Protocol

from .models import PMADecisionContext


@dataclass(frozen=True)
class PMAReasoningOutput:
    action: Literal[
        "NO_CHANGE",
        "BUY_OR_INCREASE",
        "SELL_OR_REDUCE",
        "REBALANCE",
    ]
    use_optimizer: bool
    rationale_summary: str


class PMAReasoningModel(Protocol):
    def decide(self, context: PMADecisionContext) -> PMAReasoningOutput:
        ...


_OUTLOOK_PATTERN = re.compile(
    r"^\s*Outlook:\s*(FAVORABLE|NEUTRAL|ADVERSE)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_outlook(assessment_summary: str) -> str | None:
    """Read the explicit TAA Outlook statement from the existing assessment text."""
    match = _OUTLOOK_PATTERN.search(assessment_summary or "")
    return None if match is None else match.group(1).upper()


class DeterministicPMAReasoningModel:
    """Bounded V2ET PMA reasoning from the existing TAA Assessment contract.

    PMA interprets the explicit Outlook statement contained in the TAA assessment
    text together with confidence and current Portfolio State. It does not infer
    financial direction from arbitrary words in the narrative.
    """

    def __init__(self, minimum_action_confidence: float = 0.60) -> None:
        if not 0.0 <= minimum_action_confidence <= 1.0:
            raise ValueError("minimum_action_confidence must be between 0 and 1")
        self.minimum_action_confidence = float(minimum_action_confidence)

    def decide(self, context: PMADecisionContext) -> PMAReasoningOutput:
        outlook = _extract_outlook(context.assessment_summary)

        if outlook is None:
            return PMAReasoningOutput(
                action="NO_CHANGE",
                use_optimizer=False,
                rationale_summary=(
                    "TAA assessment does not contain a valid explicit Outlook statement; "
                    "PMA makes no Portfolio change."
                ),
            )

        confidence = context.assessment_confidence
        if confidence is None or confidence < self.minimum_action_confidence:
            observed = "not provided" if confidence is None else f"{confidence:.2%}"
            return PMAReasoningOutput(
                action="NO_CHANGE",
                use_optimizer=False,
                rationale_summary=(
                    f"TAA confidence {observed} does not meet the "
                    f"{self.minimum_action_confidence:.2%} V2ET action threshold."
                ),
            )

        if outlook == "FAVORABLE":
            return PMAReasoningOutput(
                action="BUY_OR_INCREASE",
                use_optimizer=True,
                rationale_summary=(
                    f"TAA Outlook is FAVORABLE at {confidence:.2%} confidence; "
                    "PMA requests a feasible Portfolio target from PMS."
                ),
            )

        if outlook == "ADVERSE":
            has_position = any(
                position.financial_instrument_id == context.financial_instrument_id
                and position.quantity > 0
                for position in context.portfolio_state.positions
            )

            if has_position:
                return PMAReasoningOutput(
                    action="SELL_OR_REDUCE",
                    use_optimizer=True,
                    rationale_summary=(
                        f"TAA Outlook is ADVERSE at {confidence:.2%} confidence for a held "
                        "instrument; PMA requests a feasible reduced Portfolio target from PMS."
                    ),
                )

            return PMAReasoningOutput(
                action="NO_CHANGE",
                use_optimizer=False,
                rationale_summary=(
                    f"TAA Outlook is ADVERSE at {confidence:.2%} confidence, but the instrument "
                    "is not currently held; bounded V2ET does not originate short exposure."
                ),
            )

        return PMAReasoningOutput(
            action="NO_CHANGE",
            use_optimizer=False,
            rationale_summary=(
                f"TAA Outlook is NEUTRAL at {confidence:.2%} confidence; "
                "no Portfolio change is justified."
            ),
        )
