from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ExecutionContext:
    execution_id: UUID
    portfolio_decision_id: UUID
    financial_instrument_id: UUID
    symbol: str
    side: Literal["BUY", "SELL"]
    target_quantity: float
    remaining_quantity: float
    last_price: float | None
    broker_order_id: str | None
    client_order_id: str | None
    certainty_status: str
