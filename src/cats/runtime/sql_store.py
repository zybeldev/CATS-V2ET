from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cats.agents.tea import ExecutionRuntimeState
from cats.database import models


def utc_now():
    return datetime.now(timezone.utc)


class SQLExecutionStateStore:
    """SQL-backed TEA state with enough identity to reconstruct recovery safely."""

    def __init__(self, session: Session, *, environment_id: str, flow_id: str):
        self.session = session
        self.environment_id = environment_id
        self.flow_id = flow_id

    def save(self, state: ExecutionRuntimeState) -> None:
        execution = self.session.get(models.ExecutionRecord, str(state.execution_id))
        if execution is None:
            execution = models.ExecutionRecord(
                execution_id=str(state.execution_id),
                portfolio_decision_id=str(state.portfolio_decision_id),
                environment_id=self.environment_id,
                financial_instrument_id=str(state.financial_instrument_id),
                execution_type="EQUITY",
                status=state.status,
                flow_id=self.flow_id,
                symbol=state.symbol,
                side=state.side,
                target_quantity=state.target_quantity,
                client_order_id=state.client_order_id,
                broker_order_id=state.broker_order_id,
                certainty_status=state.certainty_status,
                last_execution_action_id=None if state.last_execution_action_id is None else str(state.last_execution_action_id),
            )
            self.session.add(execution)
        else:
            execution.status = state.status
            execution.symbol = state.symbol
            execution.side = state.side
            execution.target_quantity = state.target_quantity
            execution.client_order_id = state.client_order_id
            execution.broker_order_id = state.broker_order_id
            execution.certainty_status = state.certainty_status
            execution.last_execution_action_id = None if state.last_execution_action_id is None else str(state.last_execution_action_id)

        current = self.session.scalar(
            select(models.ExecutionStateRecord)
            .where(models.ExecutionStateRecord.execution_id == str(state.execution_id))
            .order_by(models.ExecutionStateRecord.effective_at.desc())
            .limit(1)
        )

        self.session.add(
            models.ExecutionStateRecord(
                execution_id=str(state.execution_id),
                prior_execution_state_id=None if current is None else current.execution_state_id,
                state_status=state.status,
                remaining_quantity=state.remaining_quantity,
                filled_quantity=state.filled_quantity,
                average_fill_price=state.average_fill_price,
                effective_at=utc_now(),
            )
        )
        self.session.commit()

    def load(self, execution_id: UUID) -> ExecutionRuntimeState | None:
        execution = self.session.get(models.ExecutionRecord, str(execution_id))
        if execution is None:
            return None
        row = self.session.scalar(
            select(models.ExecutionStateRecord)
            .where(models.ExecutionStateRecord.execution_id == str(execution_id))
            .order_by(models.ExecutionStateRecord.effective_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return ExecutionRuntimeState(
            execution_id=UUID(execution.execution_id),
            portfolio_decision_id=UUID(execution.portfolio_decision_id),
            financial_instrument_id=UUID(execution.financial_instrument_id),
            symbol=execution.symbol,
            side=execution.side,
            target_quantity=execution.target_quantity,
            remaining_quantity=row.remaining_quantity,
            client_order_id=execution.client_order_id,
            broker_order_id=execution.broker_order_id,
            filled_quantity=row.filled_quantity,
            average_fill_price=row.average_fill_price,
            certainty_status=execution.certainty_status,
            status=row.state_status,
            last_execution_action_id=None if execution.last_execution_action_id is None else UUID(execution.last_execution_action_id),
        )

    def list_active(self) -> list[ExecutionRuntimeState]:
        executions = self.session.scalars(
            select(models.ExecutionRecord).where(
                models.ExecutionRecord.environment_id == self.environment_id,
                models.ExecutionRecord.flow_id == self.flow_id,
                models.ExecutionRecord.status.notin_(["COMPLETED", "SUPERSEDED", "TERMINATED"])
            )
        ).all()

        result = []
        for execution in executions:
            state = self.load(UUID(execution.execution_id))
            if state is not None:
                result.append(state)
        return result
