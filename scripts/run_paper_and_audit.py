from __future__ import annotations

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run one CATS PAPER flow and immediately generate its audit report."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--evidence-url", action="append", required=True)
    parser.add_argument("--confirm-paper", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--output-dir", default="run_reports")
    args = parser.parse_args()

    if not args.confirm_paper:
        raise SystemExit("Blocked: --confirm-paper is required.")

    if not args.skip_preflight:
        run([sys.executable, "scripts/external_run_preflight.py"])

    flow_cmd = [
        sys.executable,
        "scripts/first_real_paper_flow.py",
        "--symbol",
        args.symbol,
        "--confirm-paper",
    ]
    for url in args.evidence_url:
        flow_cmd.extend(["--evidence-url", url])
    run(flow_cmd)

    run([
        sys.executable,
        "scripts/generate_audit_report.py",
        "--output-dir",
        args.output_dir,
    ])

    print("CATS V2ET PAPER run + audit: PASS")


if __name__ == "__main__":
    main()
