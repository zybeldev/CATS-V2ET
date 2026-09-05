from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from cats.contracts.optimization import AlternativePosition, PortfolioAlternative


@dataclass(frozen=True)
class EquityCandidate:
    financial_instrument_id: UUID
    score: float
    expected_return: float | None = None
    expected_risk: float | None = None


@dataclass(frozen=True)
class EquityOptimizationConstraints:
    max_position_weight: float
    max_total_equity_exposure: float
    min_cash_reserve_weight: float

    def __post_init__(self) -> None:
        for name, value in (
            ("max_position_weight", self.max_position_weight),
            ("max_total_equity_exposure", self.max_total_equity_exposure),
            ("min_cash_reserve_weight", self.min_cash_reserve_weight),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.max_total_equity_exposure > 1 - self.min_cash_reserve_weight + 1e-12:
            raise ValueError(
                "max_total_equity_exposure cannot exceed capital remaining after minimum cash reserve"
            )


class DeterministicEquityOptimizer:
    """Small deterministic constrained allocator for the V2E capstone.

    It converts positive candidate scores into target weights while enforcing
    portfolio-level exposure and per-position concentration constraints.
    It does not choose strategy or relax constraints.
    """

    MODEL_NAME = "V2E_SCORE_WEIGHTED_EQUITY"
    MODEL_VERSION = "1.0"

    def optimize(
        self,
        *,
        flow_id: UUID,
        source: str,
        destination: str,
        optimization_run_id: UUID,
        configuration_version_id: UUID,
        candidates: list[EquityCandidate],
        constraints: EquityOptimizationConstraints,
    ) -> PortfolioAlternative:
        diagnostics: list[str] = []

        if not candidates:
            return self._infeasible(
                flow_id=flow_id,
                source=source,
                destination=destination,
                optimization_run_id=optimization_run_id,
                configuration_version_id=configuration_version_id,
                diagnostic="No candidates supplied.",
            )

        positive = [c for c in candidates if c.score > 0]
        if not positive:
            return self._infeasible(
                flow_id=flow_id,
                source=source,
                destination=destination,
                optimization_run_id=optimization_run_id,
                configuration_version_id=configuration_version_id,
                diagnostic="No candidate has a positive optimization score.",
            )

        capacity = min(
            constraints.max_total_equity_exposure,
            1.0 - constraints.min_cash_reserve_weight,
        )
        if capacity <= 0:
            return self._infeasible(
                flow_id=flow_id,
                source=source,
                destination=destination,
                optimization_run_id=optimization_run_id,
                configuration_version_id=configuration_version_id,
                diagnostic="Governed constraints leave no allocatable equity capacity.",
            )

        weights = self._allocate(positive, capacity, constraints.max_position_weight)
        if not weights:
            return self._infeasible(
                flow_id=flow_id,
                source=source,
                destination=destination,
                optimization_run_id=optimization_run_id,
                configuration_version_id=configuration_version_id,
                diagnostic="No feasible allocation could be constructed.",
            )

        used = sum(weights.values())
        if used + 1e-9 < capacity:
            diagnostics.append(
                f"Only {used:.6f} of {capacity:.6f} equity capacity could be allocated under concentration limits."
            )

        weighted_return = self._weighted_metric(positive, weights, "expected_return")
        weighted_risk = self._weighted_metric(positive, weights, "expected_risk")
        objective = sum(c.score * weights[c.financial_instrument_id] for c in positive)

        positions = [
            AlternativePosition(
                financial_instrument_id=c.financial_instrument_id,
                target_weight=weights[c.financial_instrument_id],
            )
            for c in sorted(positive, key=lambda x: (-x.score, str(x.financial_instrument_id)))
            if weights[c.financial_instrument_id] > 0
        ]

        diagnostics.append(f"model={self.MODEL_NAME}:{self.MODEL_VERSION}")

        return PortfolioAlternative(
            flow_id=flow_id,
            source=source,
            destination=destination,
            configuration_version_id=configuration_version_id,
            portfolio_alternative_id=uuid4(),
            optimization_run_id=optimization_run_id,
            rank=1,
            feasibility_status="FEASIBLE",
            objective_value=objective,
            expected_return=weighted_return,
            expected_risk=weighted_risk,
            positions=positions,
            diagnostics=diagnostics,
            status="FINAL",
        )

    @staticmethod
    def _allocate(
        candidates: list[EquityCandidate],
        capacity: float,
        max_position_weight: float,
    ) -> dict[UUID, float]:
        ordered = sorted(candidates, key=lambda x: (-x.score, str(x.financial_instrument_id)))
        weights = {c.financial_instrument_id: 0.0 for c in ordered}
        remaining = capacity
        active = list(ordered)

        while active and remaining > 1e-12:
            total_score = sum(c.score for c in active)
            if total_score <= 0:
                break

            progress = 0.0
            next_active: list[EquityCandidate] = []
            for candidate in active:
                current = weights[candidate.financial_instrument_id]
                room = max_position_weight - current
                if room <= 1e-12:
                    continue
                proposed = remaining * candidate.score / total_score
                add = min(room, proposed)
                if add > 0:
                    weights[candidate.financial_instrument_id] += add
                    progress += add
                if room - add > 1e-12:
                    next_active.append(candidate)

            if progress <= 1e-12:
                break
            remaining -= progress
            active = next_active

        return weights

    @staticmethod
    def _weighted_metric(
        candidates: list[EquityCandidate],
        weights: dict[UUID, float],
        field: str,
    ) -> float | None:
        values: list[tuple[float, float]] = []
        for candidate in candidates:
            value = getattr(candidate, field)
            if value is not None:
                values.append((weights[candidate.financial_instrument_id], float(value)))
        total_weight = sum(w for w, _ in values)
        if total_weight <= 0:
            return None
        return sum(w * value for w, value in values) / total_weight

    @staticmethod
    def _infeasible(
        *,
        flow_id: UUID,
        source: str,
        destination: str,
        optimization_run_id: UUID,
        configuration_version_id: UUID,
        diagnostic: str,
    ) -> PortfolioAlternative:
        return PortfolioAlternative(
            flow_id=flow_id,
            source=source,
            destination=destination,
            configuration_version_id=configuration_version_id,
            portfolio_alternative_id=uuid4(),
            optimization_run_id=optimization_run_id,
            rank=1,
            feasibility_status="INFEASIBLE",
            positions=[],
            diagnostics=[diagnostic],
            status="FINAL",
        )
