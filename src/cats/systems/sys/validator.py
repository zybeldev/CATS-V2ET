from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from cats.contracts import PortfolioDecision, ValidationResult, ValidationRuleResult
from .configuration import GovernedConfiguration


@dataclass(frozen=True)
class ValidationContext:
    environment_code: str
    buying_power: float
    cash_weight: float
    current_total_equity_exposure: float
    instrument_types: dict[UUID, str]
    estimated_order_values: dict[UUID, float]
    estimated_order_quantities: dict[UUID, float]


class SystemValidator:
    """Deterministic, fail-closed implementation of the minimum V2ET SYS rules."""

    RULE_VERSION = "1.0"

    def validate(
        self,
        decision: PortfolioDecision,
        config: GovernedConfiguration,
        context: ValidationContext,
    ) -> ValidationResult:
        results: list[ValidationRuleResult] = []

        def add(code: str, passed: bool, configured=None, observed=None, reason=None):
            results.append(
                ValidationRuleResult(
                    rule_code=code,
                    rule_version=self.RULE_VERSION,
                    result="PASS" if passed else "FAIL",
                    configured_value=None if configured is None else str(configured),
                    observed_value=None if observed is None else str(observed),
                    reason=reason,
                )
            )

        add(
            "ENVIRONMENT_PAPER",
            context.environment_code == config.permitted_trading_environment,
            config.permitted_trading_environment,
            context.environment_code,
            "V2ET permits paper trading only.",
        )

        for target in decision.targets:
            instrument_type = context.instrument_types.get(target.financial_instrument_id)
            add(
                f"INSTRUMENT_TYPE:{target.financial_instrument_id}",
                instrument_type == config.permitted_instrument_type,
                config.permitted_instrument_type,
                instrument_type,
                "Only permitted instrument types may be executed.",
            )

            if target.target_weight is not None:
                add(
                    f"POSITION_WEIGHT:{target.financial_instrument_id}",
                    0 <= target.target_weight <= config.max_position_weight,
                    config.max_position_weight,
                    target.target_weight,
                    "Target weight exceeds governed concentration limit.",
                )

            estimated_value = context.estimated_order_values.get(
                target.financial_instrument_id, 0.0
            )
            add(
                f"ORDER_VALUE:{target.financial_instrument_id}",
                estimated_value <= config.max_order_value
                and estimated_value <= context.buying_power,
                min(config.max_order_value, context.buying_power),
                estimated_value,
                "Order value exceeds governed limit or available buying power.",
            )

            estimated_quantity = context.estimated_order_quantities.get(
                target.financial_instrument_id, 0.0
            )
            add(
                f"ORDER_QUANTITY:{target.financial_instrument_id}",
                abs(estimated_quantity) <= config.max_order_quantity,
                config.max_order_quantity,
                abs(estimated_quantity),
                "Order quantity exceeds governed limit.",
            )

        signed_deltas = [
            float(context.estimated_order_quantities.get(target.financial_instrument_id, 0.0))
            for target in decision.targets
        ]
        has_buy_delta = any(delta > 1e-12 for delta in signed_deltas)
        has_sell_delta = any(delta < -1e-12 for delta in signed_deltas)
        has_material_delta = has_buy_delta or has_sell_delta

        if decision.decision_type == "BUY_OR_INCREASE":
            direction_ok = has_buy_delta and not has_sell_delta
        elif decision.decision_type == "SELL_OR_REDUCE":
            direction_ok = has_sell_delta and not has_buy_delta
        elif decision.decision_type == "REBALANCE":
            direction_ok = has_material_delta
        else:  # NO_CHANGE
            direction_ok = not has_material_delta

        add(
            "DECISION_DIRECTION_CONSISTENCY",
            direction_ok,
            decision.decision_type,
            signed_deltas,
            "Portfolio Decision type must be consistent with the signed target quantity delta(s).",
        )

        add(
            "TOTAL_EQUITY_EXPOSURE",
            context.current_total_equity_exposure <= config.max_total_equity_exposure,
            config.max_total_equity_exposure,
            context.current_total_equity_exposure,
            "Total equity exposure exceeds governed limit.",
        )

        add(
            "MIN_CASH_RESERVE",
            context.cash_weight >= config.min_cash_reserve_weight,
            config.min_cash_reserve_weight,
            context.cash_weight,
            "Cash reserve is below governed minimum.",
        )

        overall = "PASS" if all(r.result == "PASS" for r in results) else "FAIL"

        return ValidationResult(
            flow_id=decision.flow_id,
            source="SYS",
            destination="TEA" if overall == "PASS" else "PMA",
            validation_result_id=uuid4(),
            portfolio_decision_id=decision.portfolio_decision_id,
            configuration_version_id=decision.configuration_version_id,
            result=overall,
            rule_results=results,
            parent_ids=[decision.portfolio_decision_id],
            status="FINAL",
        )
