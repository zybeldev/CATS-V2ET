from __future__ import annotations

import argparse
import os

from cats.runtime.real_run import require_real_run_ready


def main():
    parser = argparse.ArgumentParser(
        description="CATS V2ET first real Alpaca PAPER run launcher."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--confirm-paper",
        action="store_true",
        help="Required explicit acknowledgement that this is a PAPER run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform readiness and wiring checks without submitting an order.",
    )
    args = parser.parse_args()

    if not args.confirm_paper:
        raise SystemExit("Blocked: --confirm-paper is required.")

    require_real_run_ready()

    if args.dry_run:
        print(f"DRY RUN PASS for symbol={args.symbol.upper()}")
        print("No broker order submitted.")
        return

    # Deliberately fail closed until the final live-orchestration wiring step.
    # This protects the capstone implementation from accidentally bypassing
    # TAA -> PMA -> PMS -> SYS -> TEA -> TES.
    raise SystemExit(
        "Blocked by design: direct order submission is not permitted. "
        "Use the full CATS end-to-end orchestrator once production wiring is complete."
    )


if __name__ == "__main__":
    main()
