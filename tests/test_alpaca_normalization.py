from types import SimpleNamespace
from cats.adapters.alpaca import AlpacaPaperAdapter

class FakeTradingClient:
    def get_account(self):
        return SimpleNamespace(cash="10000.50", equity="12000.25", buying_power="15000.00", currency="USD")
    def get_all_positions(self):
        return [SimpleNamespace(symbol="AAPL", qty="10", market_value="2000.00", avg_entry_price="190.00")]

def test_normalization():
    adapter = AlpacaPaperAdapter("x", "y", trading_client=FakeTradingClient())
    assert adapter.get_account().buying_power == 15000.0
    assert adapter.get_positions()[0].quantity == 10.0
