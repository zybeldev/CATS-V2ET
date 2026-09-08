from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import mean, pstdev
from typing import Sequence

@dataclass(frozen=True)
class EquityBar:
    close: float
    volume: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    timestamp: datetime | None = None

@dataclass(frozen=True)
class EquityMeasurements:
    last_price: float
    return_1_period: float | None
    sma_short: float | None
    sma_long: float | None
    momentum: float | None
    annualized_volatility: float | None
    average_volume: float | None
    liquidity_proxy: float | None

def _ret(previous: float, current: float) -> float:
    if previous == 0:
        raise ValueError("Zero price")
    return current / previous - 1.0

class TradingSignalService:
    def calculate_equity_measurements(self, bars: Sequence[EquityBar], *, short_window=5, long_window=20, annualization_periods=252) -> EquityMeasurements:
        if not bars:
            raise ValueError("At least one bar is required")
        if short_window <= 0 or long_window <= 0 or short_window > long_window:
            raise ValueError("Invalid moving-average windows")
        closes = [float(b.close) for b in bars]
        volumes = [float(b.volume) for b in bars]
        if any(p <= 0 for p in closes):
            raise ValueError("Prices must be positive")
        if any(v < 0 for v in volumes):
            raise ValueError("Volumes cannot be negative")
        returns = [_ret(closes[i - 1], closes[i]) for i in range(1, len(closes))]
        return EquityMeasurements(
            last_price=closes[-1],
            return_1_period=returns[-1] if returns else None,
            sma_short=mean(closes[-short_window:]) if len(closes) >= short_window else None,
            sma_long=mean(closes[-long_window:]) if len(closes) >= long_window else None,
            momentum=_ret(closes[-short_window - 1], closes[-1]) if len(closes) > short_window else None,
            annualized_volatility=pstdev(returns) * sqrt(annualization_periods) if len(returns) >= 2 else None,
            average_volume=mean(volumes),
            liquidity_proxy=mean([p * v for p, v in zip(closes, volumes)]),
        )
