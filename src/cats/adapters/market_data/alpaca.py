from datetime import datetime, timedelta, timezone
from typing import Any

from cats.services.tss import EquityBar


class AlpacaMarketDataAdapter:
    def __init__(self, api_key: str, api_secret: str, stock_client: Any | None = None):
        if stock_client is None:
            from alpaca.data.historical.stock import StockHistoricalDataClient

            stock_client = StockHistoricalDataClient(api_key, api_secret)
        self.client = stock_client

    def get_latest_trade(self, symbol: str):
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockLatestTradeRequest

        clean_symbol = symbol.upper()
        request = StockLatestTradeRequest(
            symbol_or_symbols=clean_symbol,
            feed=DataFeed.IEX,
        )
        response = self.client.get_stock_latest_trade(request)
        trade = response.get(clean_symbol)
        if trade is None:
            return None
        return float(trade.price), getattr(trade, "timestamp", None)

    def get_daily_bars(self, symbol: str, lookback_days: int = 60) -> list[EquityBar]:
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        end = datetime.now(timezone.utc)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=end - timedelta(days=lookback_days),
            end=end,
            feed=DataFeed.IEX,
        )
        response = self.client.get_stock_bars(request)
        return [
            EquityBar(
                close=float(bar.close),
                volume=float(bar.volume),
                open=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                timestamp=getattr(bar, "timestamp", None),
            )
            for bar in response.data.get(symbol, [])
        ]
