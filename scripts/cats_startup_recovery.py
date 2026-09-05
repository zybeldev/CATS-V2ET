from __future__ import annotations

import json
import os

from cats.adapters.alpaca import AlpacaPaperAdapter
from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.runtime.startup_recovery import recover_outstanding_paper_flows


PREFIX = "CATS_STARTUP_RECOVERY_JSON="


def _blocked(detail: str) -> dict:
    return {
        "status": "BLOCKED",
        "checked_flow_count": 0,
        "recovered_flow_count": 0,
        "unresolved_flow_count": 0,
        "flows": [],
        "detail": detail,
    }


def main() -> int:
    """Run startup broker reconciliation independently of any LLM service."""
    environment = (os.getenv("CATS_ENVIRONMENT") or "").strip().upper()
    if environment != "PAPER":
        payload = _blocked("Startup recovery is permitted only when CATS_ENVIRONMENT=PAPER.")
        print(PREFIX + json.dumps(payload, sort_keys=True))
        return 2

    api_key = os.getenv("ALPACA_API_KEY") or os.getenv("CATS_ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET") or os.getenv("CATS_ALPACA_API_SECRET")
    if not api_key or not api_secret:
        payload = _blocked("Alpaca PAPER credentials are required for startup reconciliation.")
        print(PREFIX + json.dumps(payload, sort_keys=True))
        return 2

    try:
        broker = AlpacaPaperAdapter(api_key, api_secret)
        settings = get_settings()
        engine = create_engine_from_settings(settings)
        Session = create_session_factory(engine)
        with Session() as session:
            payload = recover_outstanding_paper_flows(session=session, broker=broker)
    except Exception as exc:
        payload = _blocked(f"{type(exc).__name__}: {exc}")
        print(PREFIX + json.dumps(payload, sort_keys=True, default=str))
        return 2

    print(PREFIX + json.dumps(payload, sort_keys=True, default=str))
    return 2 if str(payload.get("status") or "").upper() == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
