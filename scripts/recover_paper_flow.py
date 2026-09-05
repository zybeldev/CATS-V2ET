from __future__ import annotations

import argparse
import os
from uuid import UUID

from cats.adapters.alpaca import AlpacaPaperAdapter
from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.runtime.production_paper_recovery import ProductionPaperRecovery
from cats.runtime.real_run import require_real_run_ready


def main():
    parser = argparse.ArgumentParser(
        description="Recover one existing CATS V2E production PAPER flow without resubmitting orders."
    )
    parser.add_argument("--flow-id", required=True)
    parser.add_argument("--confirm-paper", action="store_true")
    args = parser.parse_args()

    if not args.confirm_paper:
        raise SystemExit("Blocked: --confirm-paper is required.")

    require_real_run_ready()
    settings = get_settings()

    alpaca_key = os.getenv("ALPACA_API_KEY") or os.getenv("CATS_ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_API_SECRET") or os.getenv("CATS_ALPACA_API_SECRET")
    if not alpaca_key or not alpaca_secret:
        raise SystemExit("Blocked: Alpaca PAPER credentials are not configured.")

    engine = create_engine_from_settings(settings)
    Session = create_session_factory(engine)
    broker = AlpacaPaperAdapter(alpaca_key, alpaca_secret)

    with Session() as session:
        result = ProductionPaperRecovery(session=session, broker=broker).recover(
            UUID(args.flow_id)
        )
        print(result)


if __name__ == "__main__":
    main()
