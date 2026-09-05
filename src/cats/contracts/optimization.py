from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .base import MaterialContract


class OptimizationRequest(MaterialContract):
    optimization_request_id: UUID
    portfolio_id: UUID
    source_portfolio_state_id: UUID
    strategic_envelope_id: UUID
    assessment_ids: list[UUID] = Field(default_factory=list)
    requested_model: str


class AlternativePosition(BaseModel):
    financial_instrument_id: UUID
    target_weight: float
    target_quantity: float | None = None


class PortfolioAlternative(MaterialContract):
    portfolio_alternative_id: UUID
    optimization_run_id: UUID
    rank: int = Field(ge=1)
    feasibility_status: Literal["FEASIBLE", "INFEASIBLE"]
    objective_value: float | None = None
    expected_return: float | None = None
    expected_risk: float | None = None
    expected_cost: float | None = None
    positions: list[AlternativePosition] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
