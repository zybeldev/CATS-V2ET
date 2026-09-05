import os

from cats.adapters.alpaca import AlpacaPaperAdapter


def main():
    api_key = os.getenv("ALPACA_API_KEY") or os.getenv("CATS_ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET") or os.getenv("CATS_ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("SKIP: Alpaca paper credentials are not configured.")

    adapter = AlpacaPaperAdapter(api_key, api_secret)
    account = adapter.get_account()
    positions = adapter.get_positions()

    print("Alpaca PAPER authentication: PASS")
    print(f"Equity: {account.equity}")
    print(f"Cash: {account.cash}")
    print(f"Buying power: {account.buying_power}")
    print(f"Positions visible: {len(positions)}")


if __name__ == "__main__":
    main()
