from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class PortfolioPositionView:
    financial_instrument_id: UUID
    symbol: str
    quantity: float
    market_value: float
    portfolio_weight: float


@dataclass(frozen=True)
class PortfolioStateView:
    portfolio_id: UUID
    portfolio_state_id: UUID
    cash_weight: float
    total_equity_exposure: float
    positions: tuple[PortfolioPositionView, ...]


@dataclass(frozen=True)
class PMADecisionContext:
    portfolio_state: PortfolioStateView
    strategic_envelope_id: UUID
    configuration_version_id: UUID
    assessment_id: UUID
    financial_instrument_id: UUID
    assessment_summary: str
    assessment_confidence: float | None
    assessment_horizon: Literal["STRATEGIC", "TACTICAL"]
