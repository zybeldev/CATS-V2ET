from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from cats.contracts import ExecutionResult
from cats.agents.pma.models import PortfolioPositionView, PortfolioStateView


@dataclass(frozen=True)
class VerifiedExecutionFact:
    financial_instrument_id: UUID
    symbol: str
    signed_quantity_delta: float
    fill_price: float


class PortfolioStateUpdater:
    """Creates a new accepted Portfolio State only from verified execution."""

    def apply_verified_execution(
        self,
        *,
        prior_state: PortfolioStateView,
        execution_result: ExecutionResult,
        fact: VerifiedExecutionFact,
        portfolio_value: float,
    ) -> PortfolioStateView:
        if not execution_result.verified:
            raise ValueError("Unverified execution cannot update authoritative Portfolio State.")
        if execution_result.result_status != "COMPLETED":
            raise ValueError("Only completed verified execution updates Portfolio State in V2E.")
        if portfolio_value <= 0:
            raise ValueError("portfolio_value must be positive.")

        by_id = {p.financial_instrument_id: p for p in prior_state.positions}
        old = by_id.get(fact.financial_instrument_id)

        old_qty = 0.0 if old is None else old.quantity
        old_mv = 0.0 if old is None else old.market_value
        new_qty = old_qty + fact.signed_quantity_delta
        new_mv = old_mv + fact.signed_quantity_delta * fact.fill_price

        if abs(new_qty) < 1e-12:
            by_id.pop(fact.financial_instrument_id, None)
        else:
            by_id[fact.financial_instrument_id] = PortfolioPositionView(
                financial_instrument_id=fact.financial_instrument_id,
                symbol=fact.symbol,
                quantity=new_qty,
                market_value=new_mv,
                portfolio_weight=new_mv / portfolio_value,
            )

        total_equity_exposure = sum(abs(p.market_value) for p in by_id.values()) / portfolio_value
        cash_weight = max(0.0, 1.0 - total_equity_exposure)

        return PortfolioStateView(
            portfolio_id=prior_state.portfolio_id,
            portfolio_state_id=uuid4(),
            cash_weight=cash_weight,
            total_equity_exposure=total_equity_exposure,
            positions=tuple(by_id.values()),
        )
