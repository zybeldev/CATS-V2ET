from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Fail-closed operator entrypoint for CATS V2ET PAPER."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("database-preflight")
    sub.add_parser("external-preflight")
    sub.add_parser("verify-latest")

    recover_parser = sub.add_parser("recover")
    recover_parser.add_argument("--flow-id", required=True)
    recover_parser.add_argument("--confirm-paper", action="store_true")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--symbol", required=True)
    run_parser.add_argument("--evidence-url", action="append", required=True)
    run_parser.add_argument("--confirm-paper", action="store_true")

    args = parser.parse_args()

    if args.command == "database-preflight":
        run([sys.executable, "scripts/local_database_preflight.py"])
    elif args.command == "external-preflight":
        run([sys.executable, "scripts/preflight_real_run.py"])
    elif args.command == "verify-latest":
        run([sys.executable, "scripts/verify_latest_flow.py"])
    elif args.command == "recover":
        if not args.confirm_paper:
            raise SystemExit("Blocked: --confirm-paper is required.")
        run([
            sys.executable,
            "scripts/recover_paper_flow.py",
            "--flow-id",
            args.flow_id,
            "--confirm-paper",
        ])
    elif args.command == "run":
        if not args.confirm_paper:
            raise SystemExit("Blocked: --confirm-paper is required.")
        cmd = [
            sys.executable,
            "scripts/first_real_paper_flow.py",
            "--symbol",
            args.symbol,
            "--confirm-paper",
        ]
        for url in args.evidence_url:
            cmd.extend(["--evidence-url", url])
        run(cmd)


if __name__ == "__main__":
    main()
