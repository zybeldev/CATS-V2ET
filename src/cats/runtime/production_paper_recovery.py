from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.contracts import ExecutionResult
from cats.database import models
from cats.repositories import (
    AcceptedPortfolioStateRepository,
    BrokerFactRepository,
    MaterialContractRepository,
)
from cats.runtime.production_paper_flow import instrument_id_for_symbol
from cats.runtime.production_persistence import utc_now
from cats.runtime.recovery import RecoveryCoordinator
from cats.runtime.sql_store import SQLExecutionStateStore
from cats.systems.tes import TradingExecutionSystem
from cats.trace import PersistentTraceService, SQLTraceRepository


@dataclass(frozen=True)
class ProductionPaperRecoveryResult:
    flow_id: UUID
    execution_ids: tuple[UUID, ...]
    completed: bool
    accepted_portfolio_state_id: UUID | None
    diagnostics: tuple[str, ...]


class ProductionPaperRecovery:
    """Resume one persisted production PAPER flow without resubmitting orders."""

    def __init__(self, *, session: Session, broker):
        self.session = session
        self.broker = broker
        self.tes = TradingExecutionSystem(broker)
        self.trace = PersistentTraceService(SQLTraceRepository(session))
        self.material = MaterialContractRepository(session)
        self.broker_facts = BrokerFactRepository(session)
        self.portfolio_states = AcceptedPortfolioStateRepository(session)

    def recover(self, flow_id: UUID) -> ProductionPaperRecoveryResult:
        flow = self.session.get(models.TraceFlow, str(flow_id))
        if flow is None:
            raise ValueError(f"TRACE_Flow {flow_id} does not exist.")
        if flow.flow_type != "PRODUCTION_PAPER":
            raise ValueError(
                f"Flow {flow_id} is {flow.flow_type}, expected PRODUCTION_PAPER."
            )

        environment = self.session.get(models.Environment, flow.environment_id)
        if environment is None or environment.environment_code != "PAPER":
            raise ValueError("Recovery is restricted to the PAPER environment.")

        executions = (
            self.session.query(models.ExecutionRecord)
            .filter_by(flow_id=str(flow_id), environment_id=flow.environment_id)
            .all()
        )
        if not executions:
            raise ValueError(f"Flow {flow_id} has no persisted executions to recover.")

        accepted = self._accepted_state_for_flow(flow_id)
        if flow.status == "COMPLETED" and accepted is not None:
            return ProductionPaperRecoveryResult(
                flow_id=flow_id,
                execution_ids=tuple(UUID(row.execution_id) for row in executions),
                completed=True,
                accepted_portfolio_state_id=UUID(accepted.portfolio_state_id),
                diagnostics=("Flow is already completed; no broker action was taken.",),
            )

        if flow.status not in {"ACTIVE", "SUSPENDED"}:
            raise ValueError(
                f"Flow {flow_id} has status {flow.status}; recovery is not allowed."
            )

        store = SQLExecutionStateStore(
            self.session,
            environment_id=flow.environment_id,
            flow_id=str(flow_id),
        )
        recovery_results = RecoveryCoordinator(store, self.tes).recover_active_executions()
        diagnostics = [item.diagnostic for item in recovery_results]
        recovery_by_execution = {item.execution_id: item for item in recovery_results}

        tea = TradingExecutionAgent(DeterministicTEAReasoningModel(), self.tes)
        reconciliation_ids: dict[str, UUID] = {}

        for execution in executions:
            state = store.load(UUID(execution.execution_id))
            if state is None:
                raise RuntimeError(
                    f"Execution {execution.execution_id} has no persisted runtime state."
                )

            recovery = recovery_by_execution.get(execution.execution_id)
            if (
                recovery is not None
                and recovery.broker_order is not None
                and state.last_execution_action_id is not None
            ):
                reconciliation_ids[execution.execution_id] = (
                    self.broker_facts.persist_reconciled_order(
                        state=state,
                        order=recovery.broker_order,
                        certainty_status=recovery.recovered_certainty,
                        resolved=recovery.resolved,
                    )
                )

            if state.status == "COMPLETED" and state.certainty_status == "CONFIRMED":
                self._ensure_execution_result(
                    flow_id=flow_id,
                    state=state,
                    tea=tea,
                    reconciliation_id=reconciliation_ids.get(execution.execution_id),
                )

            self.trace.record_event(
                flow_id=flow_id,
                event_type="EXECUTION_RECOVERY_CHECKED",
                source_component="RUNTIME",
                entity_type="TEA_Execution",
                entity_id=state.execution_id,
                status=state.status,
                payload={
                    "client_order_id": state.client_order_id,
                    "broker_order_id": state.broker_order_id,
                    "certainty_status": state.certainty_status,
                    "remaining_quantity": state.remaining_quantity,
                    "filled_quantity": state.filled_quantity,
                },
            )

        refreshed = [store.load(UUID(row.execution_id)) for row in executions]
        completed = all(
            state is not None
            and state.status == "COMPLETED"
            and state.certainty_status == "CONFIRMED"
            for state in refreshed
        )
        verified_results = all(
            self.session.query(models.ExecutionResultRecord)
            .filter_by(execution_id=row.execution_id, verified=True)
            .count()
            > 0
            for row in executions
        )

        if not completed or not verified_results:
            flow.status = "SUSPENDED"
            flow.completed_at = None
            self.session.commit()
            return ProductionPaperRecoveryResult(
                flow_id=flow_id,
                execution_ids=tuple(UUID(row.execution_id) for row in executions),
                completed=False,
                accepted_portfolio_state_id=None,
                diagnostics=tuple(diagnostics),
            )

        accepted_state_id = self._finalize_portfolio_state(flow_id)
        flow.status = "COMPLETED"
        flow.completed_at = utc_now()
        self.session.commit()

        self.trace.record_event(
            flow_id=flow_id,
            event_type="FLOW_RECOVERED",
            source_component="RUNTIME",
            entity_type="TRACE_Flow",
            entity_id=flow_id,
            status="COMPLETED",
            payload={"accepted_portfolio_state_id": str(accepted_state_id)},
        )

        return ProductionPaperRecoveryResult(
            flow_id=flow_id,
            execution_ids=tuple(UUID(row.execution_id) for row in executions),
            completed=True,
            accepted_portfolio_state_id=accepted_state_id,
            diagnostics=tuple(diagnostics),
        )

    def _ensure_execution_result(
        self,
        *,
        flow_id: UUID,
        state,
        tea: TradingExecutionAgent,
        reconciliation_id: UUID | None,
    ) -> None:
        existing = (
            self.session.query(models.ExecutionResultRecord)
            .filter_by(execution_id=str(state.execution_id), verified=True)
            .first()
        )
        if existing is not None:
            return

        result = tea.run_cycle(state=state)
        if not isinstance(result, ExecutionResult) or not result.verified:
            raise RuntimeError(
                f"Execution {state.execution_id} did not produce a verified final result."
            )

        result = result.model_copy(
            update={
                "flow_id": flow_id,
                "reconciliation_id": reconciliation_id,
            }
        )
        self.material.persist_execution_result(result)
        self.material.commit()

    def _accepted_state_for_flow(self, flow_id: UUID):
        decisions = (
            self.session.query(models.PortfolioDecisionRecord)
            .filter_by(flow_id=str(flow_id))
            .all()
        )
        if len(decisions) != 1:
            return None
        return (
            self.session.query(models.PortfolioState)
            .filter_by(
                source_portfolio_decision_id=decisions[0].portfolio_decision_id,
                status="ACCEPTED",
            )
            .first()
        )

    def _finalize_portfolio_state(self, flow_id: UUID) -> UUID:
        decisions = (
            self.session.query(models.PortfolioDecisionRecord)
            .filter_by(flow_id=str(flow_id))
            .all()
        )
        if len(decisions) != 1:
            raise RuntimeError(
                f"Flow {flow_id} must have exactly one portfolio decision; found {len(decisions)}."
            )
        decision = decisions[0]

        existing = (
            self.session.query(models.PortfolioState)
            .filter_by(
                source_portfolio_decision_id=decision.portfolio_decision_id,
                status="ACCEPTED",
            )
            .first()
        )
        if existing is not None:
            return UUID(existing.portfolio_state_id)

        account = self.broker.get_account()
        positions = self.broker.get_positions()
        position_facts = []

        for position in positions:
            instrument_id = instrument_id_for_symbol(position.symbol)
            if self.session.get(models.FinancialInstrument, str(instrument_id)) is None:
                self.session.add(
                    models.FinancialInstrument(
                        financial_instrument_id=str(instrument_id),
                        instrument_type="EQUITY",
                        symbol=position.symbol.upper(),
                        status="ACTIVE",
                    )
                )
            position_facts.append(
                {
                    "financial_instrument_id": instrument_id,
                    "quantity": position.quantity,
                    "average_cost": position.average_entry_price,
                    "market_value": position.market_value,
                    "currency": account.currency,
                }
            )

        self.session.flush()
        accepted_state_id = self.portfolio_states.persist_broker_confirmed_state(
            portfolio_id=UUID(decision.portfolio_id),
            prior_portfolio_state_id=UUID(decision.source_portfolio_state_id),
            source_portfolio_decision_id=UUID(decision.portfolio_decision_id),
            configuration_version_id=UUID(decision.configuration_version_id),
            cash=float(account.cash),
            equity=float(account.equity),
            buying_power=float(account.buying_power),
            positions=position_facts,
        )

        existing_lineage = (
            self.session.query(models.TraceLineageLinkRecord)
            .filter_by(
                flow_id=str(flow_id),
                parent_entity_type="PMA_Portfolio_Decision",
                parent_entity_id=decision.portfolio_decision_id,
                child_entity_type="PMA_Portfolio_State",
                child_entity_id=str(accepted_state_id),
                relationship_type="REALIZED_AS",
            )
            .first()
        )
        if existing_lineage is None:
            self.trace.add_lineage(
                flow_id=flow_id,
                parent_entity_type="PMA_Portfolio_Decision",
                parent_entity_id=UUID(decision.portfolio_decision_id),
                child_entity_type="PMA_Portfolio_State",
                child_entity_id=accepted_state_id,
                relationship_type="REALIZED_AS",
                sequence_number=4,
            )

        return accepted_state_id
