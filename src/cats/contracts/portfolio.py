from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .base import MaterialContract


class DecisionTarget(BaseModel):
    financial_instrument_id: UUID
    target_weight: float | None = None
    target_quantity: float | None = None


class PortfolioDecision(MaterialContract):
    portfolio_decision_id: UUID
    portfolio_id: UUID
    source_portfolio_state_id: UUID
    decision_type: Literal["NO_CHANGE", "BUY_OR_INCREASE", "SELL_OR_REDUCE", "REBALANCE"]
    horizon: Literal["STRATEGIC", "TACTICAL"]
    strategic_envelope_id: UUID
    selected_portfolio_alternative_id: UUID | None = None
    assessment_ids: list[UUID] = Field(default_factory=list)
    targets: list[DecisionTarget] = Field(default_factory=list)
    rationale_summary: str
