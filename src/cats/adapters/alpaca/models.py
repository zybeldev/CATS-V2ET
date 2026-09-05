from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class BrokerOrder:
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    submitted_at: datetime | None = None

@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: float
    market_value: float | None
    average_entry_price: float | None

@dataclass(frozen=True)
class BrokerAccount:
    cash: float
    equity: float
    buying_power: float
    currency: str = "USD"

@dataclass(frozen=True)
class BrokerActionOutcome:
    certainty_status: Literal["CONFIRMED", "REJECTED", "PARTIAL", "CANCELED", "UNKNOWN_OUTCOME"]
    order: BrokerOrder | None = None
    error_code: str | None = None
    error_message: str | None = None
