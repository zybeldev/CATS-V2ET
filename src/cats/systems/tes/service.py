from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cats.adapters.alpaca import BrokerActionOutcome, BrokerOrder


class BrokerAdapter(Protocol):
    def submit_market_order(self, *, symbol: str, quantity: float, side: str, client_order_id: str) -> BrokerActionOutcome:
        ...
    def get_order_by_client_order_id(self, client_order_id: str) -> BrokerOrder | None:
        ...


@dataclass(frozen=True)
class ReconciliationResult:
    certainty_status: str
    broker_order: BrokerOrder | None
    resolved: bool
    diagnostic: str


class TradingExecutionSystem:
    """Deterministic broker mechanics only."""

    def __init__(self, broker: BrokerAdapter):
        self.broker = broker

    def submit_market(
        self,
        *,
        symbol: str,
        quantity: float,
        side: str,
        client_order_id: str,
    ) -> BrokerActionOutcome:
        return self.broker.submit_market_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            client_order_id=client_order_id,
        )

    def reconcile_by_client_order_id(self, client_order_id: str) -> ReconciliationResult:
        order = self.broker.get_order_by_client_order_id(client_order_id)
        if order is None:
            return ReconciliationResult(
                certainty_status="UNKNOWN_OUTCOME",
                broker_order=None,
                resolved=False,
                diagnostic="No definitive broker order found for client_order_id.",
            )

        status = order.status.upper()
        if order.filled_quantity > 0 and status not in {"FILLED"}:
            certainty = "PARTIAL"
        elif status == "FILLED":
            certainty = "CONFIRMED"
        elif status in {"CANCELED", "CANCELLED"}:
            certainty = "CANCELED"
        elif status in {"REJECTED"}:
            certainty = "REJECTED"
        else:
            certainty = "CONFIRMED"

        return ReconciliationResult(
            certainty_status=certainty,
            broker_order=order,
            resolved=True,
            diagnostic=f"Broker order located with status={status}.",
        )
