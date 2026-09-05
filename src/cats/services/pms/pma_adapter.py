from __future__ import annotations

from uuid import uuid4

from cats.contracts import OptimizationRequest, PortfolioAlternative
from .optimizer import (
    DeterministicEquityOptimizer,
    EquityCandidate,
    EquityOptimizationConstraints,
)


class PMAOptimizerAdapter:
    """Adapts deterministic PMS to PMA and preserves the exact material artifacts."""

    def __init__(self, optimizer: DeterministicEquityOptimizer | None = None):
        self.optimizer = optimizer or DeterministicEquityOptimizer()
        self.last_request: OptimizationRequest | None = None
        self.last_alternative: PortfolioAlternative | None = None

    def optimize(
        self,
        request: OptimizationRequest,
        *,
        candidates: list[EquityCandidate],
        constraints: EquityOptimizationConstraints,
        portfolio_value: float,
        prices_by_instrument: dict,
    ) -> PortfolioAlternative:
        if portfolio_value <= 0:
            raise ValueError("portfolio_value must be positive")

        self.last_request = request
        alternative = self.optimizer.optimize(
            flow_id=request.flow_id,
            source="PMS",
            destination="PMA",
            optimization_run_id=uuid4(),
            configuration_version_id=request.configuration_version_id,
            candidates=candidates,
            constraints=constraints,
        )

        if alternative.feasibility_status != "FEASIBLE":
            self.last_alternative = alternative
            return alternative

        updated = []
        for position in alternative.positions:
            price = float(prices_by_instrument[position.financial_instrument_id])
            if price <= 0:
                raise ValueError("instrument price must be positive")
            target_quantity = (portfolio_value * position.target_weight) / price
            updated.append(position.model_copy(update={"target_quantity": target_quantity}))

        materialized = alternative.model_copy(update={"positions": updated})
        self.last_alternative = materialized
        return materialized
