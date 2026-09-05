from cats.services.tss import EquityBar, TradingSignalService

def test_tss_is_deterministic():
    bars = [EquityBar(100 + i, 1_000_000 + i * 1000) for i in range(25)]
    service = TradingSignalService()
    a = service.calculate_equity_measurements(bars)
    b = service.calculate_equity_measurements(bars)
    assert a == b
    assert a.last_price == 124
    assert not hasattr(a, "recommendation")
