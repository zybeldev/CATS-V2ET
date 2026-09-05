from __future__ import annotations
from typing import Any
from .models import BrokerAccount, BrokerActionOutcome, BrokerOrder, BrokerPosition

class AlpacaPaperAdapter:
    def __init__(self, api_key: str, api_secret: str, trading_client: Any | None = None):
        if trading_client is None:
            from alpaca.trading.client import TradingClient
            trading_client = TradingClient(api_key, api_secret, paper=True)
        self.client = trading_client

    @staticmethod
    def _f(value, default=0.0):
        return default if value is None else float(value)

    @staticmethod
    def _e(value):
        return getattr(value, "value", str(value))

    def _normalize_order(self, order: Any) -> BrokerOrder:
        return BrokerOrder(
            broker_order_id=str(order.id),
            client_order_id=str(order.client_order_id),
            symbol=str(order.symbol),
            side=self._e(order.side).upper(),
            quantity=self._f(order.qty),
            order_type=self._e(order.type).upper(),
            status=self._e(order.status).upper(),
            filled_quantity=self._f(getattr(order, "filled_qty", 0.0)),
            average_fill_price=None if getattr(order, "filled_avg_price", None) is None else self._f(order.filled_avg_price),
            submitted_at=getattr(order, "submitted_at", None),
        )

    def submit_market_order(self, *, symbol: str, quantity: float, side: str, client_order_id: str) -> BrokerActionOutcome:
        try:
            from alpaca.trading.enums import OrderSide, TimeInForce
            from alpaca.trading.requests import MarketOrderRequest
            request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                client_order_id=client_order_id,
            )
            order = self.client.submit_order(order_data=request)
            return BrokerActionOutcome("CONFIRMED", self._normalize_order(order))
        except TimeoutError as exc:
            return BrokerActionOutcome("UNKNOWN_OUTCOME", error_code="TIMEOUT", error_message=str(exc))
        except Exception as exc:
            return BrokerActionOutcome("UNKNOWN_OUTCOME", error_code=type(exc).__name__, error_message=str(exc))

    def get_order_by_client_order_id(self, client_order_id: str) -> BrokerOrder | None:
        try:
            return self._normalize_order(self.client.get_order_by_client_id(client_order_id))
        except Exception:
            return None

    def cancel_order(self, broker_order_id: str) -> BrokerActionOutcome:
        try:
            self.client.cancel_order_by_id(broker_order_id)
            return BrokerActionOutcome("CANCELED")
        except Exception as exc:
            return BrokerActionOutcome("UNKNOWN_OUTCOME", error_code=type(exc).__name__, error_message=str(exc))

    def get_account(self) -> BrokerAccount:
        account = self.client.get_account()
        return BrokerAccount(self._f(account.cash), self._f(account.equity), self._f(account.buying_power), str(getattr(account, "currency", "USD")))

    def get_positions(self) -> list[BrokerPosition]:
        return [
            BrokerPosition(
                symbol=str(p.symbol),
                quantity=self._f(p.qty),
                market_value=None if getattr(p, "market_value", None) is None else self._f(p.market_value),
                average_entry_price=None if getattr(p, "avg_entry_price", None) is None else self._f(p.avg_entry_price),
            )
            for p in self.client.get_all_positions()
        ]
