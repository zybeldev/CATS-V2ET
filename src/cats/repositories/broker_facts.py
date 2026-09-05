from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from cats.adapters.alpaca.models import BrokerOrder
from cats.agents.tea import ExecutionRuntimeState
from cats.database import models


def utc_now():
    return datetime.now(timezone.utc)


class BrokerFactRepository:
    """Persists normalized broker facts after submission/reconciliation."""

    def __init__(self, session: Session):
        self.session = session

    def persist_reconciled_order(
        self,
        *,
        state: ExecutionRuntimeState,
        order: BrokerOrder,
        certainty_status: str,
        resolved: bool,
    ) -> UUID:
        if state.last_execution_action_id is None:
            raise ValueError("Execution action identity is required for broker persistence.")

        latest_state = (
            self.session.query(models.ExecutionStateRecord)
            .filter_by(execution_id=str(state.execution_id))
            .order_by(models.ExecutionStateRecord.effective_at.desc())
            .first()
        )
        if latest_state is None:
            raise ValueError("Execution state must be persisted before broker facts.")

        action_id = str(state.last_execution_action_id)
        action = self.session.get(models.ExecutionActionRecord, action_id)
        if action is None:
            action = models.ExecutionActionRecord(
                execution_action_id=action_id,
                execution_id=str(state.execution_id),
                execution_state_id=latest_state.execution_state_id,
                action_type="SUBMIT",
                client_action_id=order.client_order_id,
                requested_at=order.submitted_at or utc_now(),
                status="COMPLETED" if resolved else "UNCERTAIN",
                attempt_number=1,
                certainty_status=certainty_status,
            )
            self.session.add(action)

        existing_order = (
            self.session.query(models.OrderRecord)
            .filter_by(client_order_id=order.client_order_id)
            .one_or_none()
        )
        if existing_order is None:
            order_row = models.OrderRecord(
                execution_action_id=action_id,
                execution_id=str(state.execution_id),
                financial_instrument_id=str(state.financial_instrument_id),
                client_order_id=order.client_order_id,
                broker_order_id=order.broker_order_id,
                order_type=order.order_type,
                side=order.side,
                quantity=order.quantity,
                limit_price=None,
                status=order.status,
            )
            self.session.add(order_row)
            self.session.flush()
        else:
            order_row = existing_order
            order_row.broker_order_id = order.broker_order_id
            order_row.status = order.status

        self.session.add(
            models.BrokerActionResultRecord(
                execution_action_id=action_id,
                order_id=order_row.order_id,
                broker_order_id=order.broker_order_id,
                broker_status=order.status,
                certainty_status=certainty_status,
            )
        )

        reconciliation_id = uuid4()
        self.session.add(
            models.ReconciliationRecord(
                reconciliation_id=str(reconciliation_id),
                execution_id=str(state.execution_id),
                client_order_id=order.client_order_id,
                broker_order_id=order.broker_order_id,
                certainty_status=certainty_status,
                resolved=resolved,
                broker_status=order.status,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                reconciled_at=utc_now(),
            )
        )

        if order.filled_quantity > 0 and order.average_fill_price is not None:
            existing_fill = (
                self.session.query(models.FillRecord)
                .filter_by(
                    order_id=order_row.order_id,
                    quantity=order.filled_quantity,
                    price=order.average_fill_price,
                )
                .first()
            )
            if existing_fill is None:
                self.session.add(
                    models.FillRecord(
                        order_id=order_row.order_id,
                        execution_id=str(state.execution_id),
                        broker_fill_reference=order.broker_order_id,
                        quantity=order.filled_quantity,
                        price=order.average_fill_price,
                        filled_at=utc_now(),
                    )
                )

        self.session.commit()
        return reconciliation_id
