from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from cats.contracts import (
    BrokerExecutionResult,
    ExecutionActionRequest,
    ExecutionResult,
    PortfolioDecision,
    ValidationResult,
)
from cats.systems.tes import TradingExecutionSystem
from .models import ExecutionContext
from .reasoning import TEAReasoningModel


@dataclass
class ExecutionRuntimeState:
    execution_id: UUID
    portfolio_decision_id: UUID
    financial_instrument_id: UUID
    symbol: str
    side: str
    target_quantity: float
    remaining_quantity: float
    client_order_id: str | None = None
    broker_order_id: str | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    certainty_status: str = "NOT_SUBMITTED"
    status: str = "ACTIVE"
    last_execution_action_id: UUID | None = None


class TradingExecutionAgent:
    """TEA executes SYS-approved PMA intent without redefining the target."""

    DEFAULT_EXECUTION_WEIGHT_TOLERANCE = 0.0005  # +/- 0.05 percentage points

    def __init__(
        self,
        reasoning_model: TEAReasoningModel,
        tes: TradingExecutionSystem,
        *,
        execution_weight_tolerance: float = DEFAULT_EXECUTION_WEIGHT_TOLERANCE,
    ):
        if execution_weight_tolerance < 0:
            raise ValueError("execution_weight_tolerance must be non-negative")
        self.reasoning_model = reasoning_model
        self.tes = tes
        self.execution_weight_tolerance = float(execution_weight_tolerance)

    def start_execution(
        self,
        *,
        decision: PortfolioDecision,
        validation: ValidationResult,
        symbol_by_instrument: dict[UUID, str],
        current_quantity_by_instrument: dict[UUID, float] | None = None,
        current_weight_by_instrument: dict[UUID, float] | None = None,
    ) -> list[ExecutionRuntimeState]:
        if validation.result != "PASS":
            raise ValueError("TEA cannot execute a SYS validation failure.")
        if validation.portfolio_decision_id != decision.portfolio_decision_id:
            raise ValueError("Validation does not correspond to PortfolioDecision.")

        states: list[ExecutionRuntimeState] = []
        current_quantity_by_instrument = current_quantity_by_instrument or {}
        current_weight_by_instrument = current_weight_by_instrument or {}
        for target in decision.targets:
            if target.target_quantity is None:
                continue

            # Execution-completion tolerance is a TEA concern. If broker-confirmed
            # current weight already satisfies the PMA-authorized target within the
            # standard execution tolerance, no order is required. The exact PMA/PMS
            # target remains unchanged; the residual stays in realized Portfolio State.
            if (
                target.target_weight is not None
                and target.financial_instrument_id in current_weight_by_instrument
            ):
                current_weight = float(
                    current_weight_by_instrument[target.financial_instrument_id]
                )
                if abs(float(target.target_weight) - current_weight) <= self.execution_weight_tolerance:
                    continue

            current_quantity = float(current_quantity_by_instrument.get(target.financial_instrument_id, 0.0))
            delta = float(target.target_quantity) - current_quantity
            if abs(delta) < 1e-12:
                continue
            side = "BUY" if delta > 0 else "SELL"
            qty = abs(delta)
            states.append(
                ExecutionRuntimeState(
                    execution_id=uuid4(),
                    portfolio_decision_id=decision.portfolio_decision_id,
                    financial_instrument_id=target.financial_instrument_id,
                    symbol=symbol_by_instrument[target.financial_instrument_id],
                    side=side,
                    target_quantity=qty,
                    remaining_quantity=qty,
                )
            )
        return states

    def run_cycle(
        self,
        *,
        state: ExecutionRuntimeState,
        last_price: float | None = None,
    ) -> BrokerExecutionResult | ExecutionResult | None:
        context = ExecutionContext(
            execution_id=state.execution_id,
            portfolio_decision_id=state.portfolio_decision_id,
            financial_instrument_id=state.financial_instrument_id,
            symbol=state.symbol,
            side=state.side,
            target_quantity=state.target_quantity,
            remaining_quantity=state.remaining_quantity,
            last_price=last_price,
            broker_order_id=state.broker_order_id,
            client_order_id=state.client_order_id,
            certainty_status=state.certainty_status,
        )
        decision = self.reasoning_model.decide(context)

        if decision.action == "COMPLETE":
            state.status = "COMPLETED"
            return ExecutionResult(
                flow_id=uuid4(),
                source="TEA",
                destination="PMA",
                execution_result_id=uuid4(),
                execution_id=state.execution_id,
                portfolio_decision_id=state.portfolio_decision_id,
                result_status="COMPLETED",
                verified=True,
                status="FINAL",
            )

        if decision.action == "SUSPEND":
            state.status = "SUSPENDED"
            return ExecutionResult(
                flow_id=uuid4(),
                source="TEA",
                destination="PMA",
                execution_result_id=uuid4(),
                execution_id=state.execution_id,
                portfolio_decision_id=state.portfolio_decision_id,
                result_status="SUSPENDED",
                verified=False,
                status="FINAL",
            )

        if decision.action == "WAIT":
            return None

        if decision.action == "RECONCILE":
            if not state.client_order_id:
                state.status = "SUSPENDED"
                return ExecutionResult(
                    flow_id=uuid4(),
                    source="TEA",
                    destination="PMA",
                    execution_result_id=uuid4(),
                    execution_id=state.execution_id,
                    portfolio_decision_id=state.portfolio_decision_id,
                    result_status="SUSPENDED",
                    verified=False,
                    status="FINAL",
                )

            rec = self.tes.reconcile_by_client_order_id(state.client_order_id)
            state.certainty_status = rec.certainty_status
            if rec.broker_order:
                state.broker_order_id = rec.broker_order.broker_order_id
                state.filled_quantity = rec.broker_order.filled_quantity
                state.average_fill_price = rec.broker_order.average_fill_price
                if rec.broker_order.status.upper() == "FILLED":
                    # Broker-confirmed FILLED is authoritative even if a fractional
                    # quantity is reported with slightly different decimal precision.
                    state.remaining_quantity = 0.0
                else:
                    state.remaining_quantity = max(0.0, state.target_quantity - state.filled_quantity)

            if rec.resolved and state.remaining_quantity <= 0:
                state.status = "COMPLETED"
                return ExecutionResult(
                    flow_id=uuid4(),
                    source="TEA",
                    destination="PMA",
                    execution_result_id=uuid4(),
                    execution_id=state.execution_id,
                    portfolio_decision_id=state.portfolio_decision_id,
                    result_status="COMPLETED",
                    verified=True,
                    status="FINAL",
                )
            return None

        if decision.action == "SUBMIT_MARKET":
            if decision.quantity is None or decision.quantity <= 0:
                raise ValueError("Execution quantity must be positive.")
            if decision.quantity > state.remaining_quantity:
                raise ValueError("TEA may not exceed PMA-authorized remaining quantity.")

            state.client_order_id = state.client_order_id or f"cats-{state.execution_id.hex}"
            action = ExecutionActionRequest(
                flow_id=uuid4(),
                source="TEA",
                destination="TES",
                execution_action_id=uuid4(),
                execution_id=state.execution_id,
                financial_instrument_id=state.financial_instrument_id,
                action_type="SUBMIT",
                side=state.side,
                quantity=decision.quantity,
                order_type="MARKET",
                client_order_id=state.client_order_id,
                status="REQUESTED",
            )
            state.last_execution_action_id = action.execution_action_id
            outcome = self.tes.submit_market(
                symbol=state.symbol,
                quantity=decision.quantity,
                side=state.side,
                client_order_id=state.client_order_id,
            )

            state.certainty_status = outcome.certainty_status
            if outcome.order:
                state.broker_order_id = outcome.order.broker_order_id
                state.filled_quantity = outcome.order.filled_quantity
                state.average_fill_price = outcome.order.average_fill_price
                state.remaining_quantity = max(0.0, state.target_quantity - state.filled_quantity)

            return BrokerExecutionResult(
                flow_id=action.flow_id,
                source="TES",
                destination="TEA",
                execution_action_id=action.execution_action_id,
                execution_id=state.execution_id,
                broker_order_id=state.broker_order_id,
                certainty_status=outcome.certainty_status,
                broker_status=None if outcome.order is None else outcome.order.status,
                filled_quantity=state.filled_quantity,
                average_fill_price=state.average_fill_price,
                error_code=outcome.error_code,
                error_message=outcome.error_message,
                status="FINAL",
                parent_ids=[action.execution_action_id],
            )

        raise RuntimeError(f"Unsupported TEA action: {decision.action}")
