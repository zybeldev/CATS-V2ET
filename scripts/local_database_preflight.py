from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    run([sys.executable, "scripts/check_postgres.py"])
    run([sys.executable, "scripts/run_migrations.py"])
    run([sys.executable, "scripts/verify_schema.py"])
    print("Local database preflight: PASS")


if __name__ == "__main__":
    main()
