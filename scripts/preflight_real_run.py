from __future__ import annotations

import os
import subprocess
import sys

from cats.runtime.real_run import require_real_run_ready


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    require_real_run_ready()

    run([sys.executable, "scripts/check_postgres.py"])
    run([sys.executable, "scripts/run_migrations.py"])
    run([sys.executable, "scripts/alpaca_smoke_test.py"])
    run([sys.executable, "scripts/openai_smoke_test.py"])

    print("CATS V2E external preflight: PASS")
    print("System is ready for the first real PAPER end-to-end flow.")


if __name__ == "__main__":
    main()
