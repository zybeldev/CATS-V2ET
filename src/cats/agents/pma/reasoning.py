from __future__ import annotations

from dataclasses import dataclass
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


class DeterministicPMAReasoningModel:
    """Testing/demo reasoning model.

    This is intentionally simple. It demonstrates the PMA authority boundary
    without pretending to be a production investment model.
    """

    def decide(self, context: PMADecisionContext) -> PMAReasoningOutput:
        text = context.assessment_summary.lower()

        if any(term in text for term in ("material risk", "deterioration", "reduce exposure")):
            return PMAReasoningOutput(
                action="SELL_OR_REDUCE",
                use_optimizer=True,
                rationale_summary="Assessment indicates material downside or deterioration.",
            )

        if any(term in text for term in ("attractive", "positive", "increase exposure", "opportunity")):
            return PMAReasoningOutput(
                action="BUY_OR_INCREASE",
                use_optimizer=True,
                rationale_summary="Assessment indicates a portfolio-relevant positive opportunity.",
            )

        return PMAReasoningOutput(
            action="NO_CHANGE",
            use_optimizer=False,
            rationale_summary="Assessment does not justify a portfolio change.",
        )
