from __future__ import annotations

from dataclasses import dataclass

from cats.adapters.alpaca import BrokerOrder
from cats.agents.tea.agent import ExecutionRuntimeState
from cats.systems.tes import TradingExecutionSystem
from .persistence import ExecutionStateStore


@dataclass(frozen=True)
class RecoveryResult:
    execution_id: str
    previous_certainty: str
    recovered_certainty: str
    status: str
    diagnostic: str
    broker_order: BrokerOrder | None = None
    resolved: bool = False


class RecoveryCoordinator:
    """Recover execution state from durable CATS state + broker reality."""

    def __init__(self, store: ExecutionStateStore, tes: TradingExecutionSystem):
        self.store = store
        self.tes = tes

    def recover_active_executions(self) -> list[RecoveryResult]:
        results: list[RecoveryResult] = []

        for state in self.store.list_active():
            previous = state.certainty_status
            broker_order = None
            resolved = False

            if state.client_order_id:
                rec = self.tes.reconcile_by_client_order_id(state.client_order_id)
                state.certainty_status = rec.certainty_status
                broker_order = rec.broker_order
                resolved = rec.resolved

                if rec.broker_order:
                    state.broker_order_id = rec.broker_order.broker_order_id
                    state.filled_quantity = rec.broker_order.filled_quantity
                    state.average_fill_price = rec.broker_order.average_fill_price
                    if rec.broker_order.status.upper() == "FILLED":
                        # Broker status is authoritative. Fractional-share quantities may
                        # be normalized/rounded by the broker, so do not leave a tiny
                        # synthetic remainder after a broker-confirmed FILLED order.
                        state.remaining_quantity = 0.0
                    else:
                        state.remaining_quantity = max(
                            0.0, state.target_quantity - state.filled_quantity
                        )

                if rec.resolved and state.remaining_quantity <= 0:
                    state.status = "COMPLETED"
                elif not rec.resolved:
                    state.status = "SUSPENDED"

                diagnostic = rec.diagnostic
            else:
                diagnostic = "No broker action identity exists; internal state is resumable."

            self.store.save(state)
            results.append(
                RecoveryResult(
                    execution_id=str(state.execution_id),
                    previous_certainty=previous,
                    recovered_certainty=state.certainty_status,
                    status=state.status,
                    diagnostic=diagnostic,
                    broker_order=broker_order,
                    resolved=resolved,
                )
            )

        return results
