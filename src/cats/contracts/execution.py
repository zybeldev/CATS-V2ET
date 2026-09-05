from typing import Literal
from uuid import UUID

from pydantic import Field

from .base import MaterialContract


class ExecutionActionRequest(MaterialContract):
    execution_action_id: UUID
    execution_id: UUID
    financial_instrument_id: UUID
    action_type: Literal["SUBMIT", "CANCEL", "REPLACE", "QUERY"]
    side: Literal["BUY", "SELL"] | None = None
    quantity: float | None = Field(default=None, gt=0)
    order_type: Literal["MARKET", "LIMIT"] | None = None
    limit_price: float | None = Field(default=None, gt=0)
    client_order_id: str | None = None


class BrokerExecutionResult(MaterialContract):
    execution_action_id: UUID
    execution_id: UUID
    broker_order_id: str | None = None
    certainty_status: Literal[
        "CONFIRMED",
        "REJECTED",
        "PARTIAL",
        "CANCELED",
        "UNKNOWN_OUTCOME",
    ]
    broker_status: str | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    error_code: str | None = None
    error_message: str | None = None


class ExecutionResult(MaterialContract):
    execution_result_id: UUID
    execution_id: UUID
    portfolio_decision_id: UUID
    result_status: Literal["COMPLETED", "PARTIAL", "FAILED", "SUSPENDED"]
    reconciliation_id: UUID | None = None
    verified: bool = False
