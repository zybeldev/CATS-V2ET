from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cats.agents.tea import PersistentTradingExecutionAgent
from cats.contracts import ExecutionResult
from cats.runtime.recovery import RecoveryCoordinator
from cats.runtime.sql_store import SQLExecutionStateStore
from cats.trace import PersistentTraceService


@dataclass(frozen=True)
class PersistentExecutionOutcome:
    execution_id: UUID
    completed: bool
    verified: bool
    execution_result: ExecutionResult | None


class PersistentExecutionCoordinator:
    """Durable TEA/TES execution boundary for the real PAPER flow."""

    def __init__(
        self,
        *,
        tea,
        store: SQLExecutionStateStore,
        trace: PersistentTraceService,
        tes,
        broker_fact_repository=None,
        material_repository=None,
    ):
        self.tea = tea
        self.store = store
        self.trace = trace
        self.tes = tes
        self.broker_fact_repository = broker_fact_repository
        self.material_repository = material_repository
        self.persistent_tea = PersistentTradingExecutionAgent(tea, store)

    def _persist_broker_fact(self, state) -> UUID | None:
        if (
            self.broker_fact_repository is None
            or not state.client_order_id
            or state.last_execution_action_id is None
        ):
            return None
        rec = self.tes.reconcile_by_client_order_id(state.client_order_id)
        if rec.broker_order is None:
            return None
        reconciliation_id = self.broker_fact_repository.persist_reconciled_order(
            state=state,
            order=rec.broker_order,
            certainty_status=rec.certainty_status,
            resolved=rec.resolved,
        )
        return reconciliation_id

    def execute_states(self, *, flow_id, states, last_price) -> list[PersistentExecutionOutcome]:
        self.persistent_tea.persist_new_states(states)
        outcomes = []

        for state in states:
            self.trace.record_event(
                flow_id=flow_id,
                event_type="EXECUTION_STARTED",
                source_component="TEA",
                entity_type="TEA_Execution",
                entity_id=state.execution_id,
                status="ACTIVE",
                payload={
                    "symbol": state.symbol,
                    "side": state.side,
                    "target_quantity": state.target_quantity,
                },
            )

            self.persistent_tea.run_cycle(
                execution_id=state.execution_id,
                last_price=last_price,
            )

            persisted = self.store.load(state.execution_id)
            if persisted is not None and persisted.certainty_status == "UNKNOWN_OUTCOME":
                self.trace.record_event(
                    flow_id=flow_id,
                    event_type="EXECUTION_OUTCOME_UNKNOWN",
                    source_component="TEA",
                    entity_type="TEA_Execution",
                    entity_id=state.execution_id,
                    status="UNCERTAIN",
                    payload={"client_order_id": persisted.client_order_id},
                )
                RecoveryCoordinator(self.store, self.tes).recover_active_executions()

            persisted = self.store.load(state.execution_id)
            reconciliation_id = None
            if persisted is not None:
                reconciliation_id = self._persist_broker_fact(persisted)

            final = self.persistent_tea.run_cycle(
                execution_id=state.execution_id,
                last_price=last_price,
            )
            persisted = self.store.load(state.execution_id)

            if final is not None and reconciliation_id is not None:
                final = final.model_copy(update={"reconciliation_id": reconciliation_id})

            verified = bool(final and getattr(final, "verified", False))
            completed = bool(persisted and persisted.status == "COMPLETED")

            if final is not None and self.material_repository is not None:
                self.material_repository.persist_execution_result(final)
                self.material_repository.commit()

            self.trace.record_event(
                flow_id=flow_id,
                event_type="EXECUTION_FINISHED",
                source_component="TEA",
                entity_type="TEA_Execution",
                entity_id=state.execution_id,
                status="COMPLETED" if completed else (persisted.status if persisted else "UNKNOWN"),
                payload={
                    "verified": verified,
                    "filled_quantity": None if persisted is None else persisted.filled_quantity,
                    "average_fill_price": None if persisted is None else persisted.average_fill_price,
                    "reconciliation_id": None if reconciliation_id is None else str(reconciliation_id),
                },
            )
            outcomes.append(
                PersistentExecutionOutcome(
                    execution_id=state.execution_id,
                    completed=completed,
                    verified=verified,
                    execution_result=final,
                )
            )
        return outcomes
