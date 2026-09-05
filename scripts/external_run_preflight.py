from __future__ import annotations

import subprocess
import sys


STEPS = [
    ("Environment doctor", [sys.executable, "scripts/environment_doctor.py"]),
    ("PostgreSQL connectivity", [sys.executable, "scripts/check_postgres.py"]),
    ("Database migrations", [sys.executable, "scripts/run_migrations.py"]),
    ("Schema verification", [sys.executable, "scripts/verify_schema.py"]),
    ("Alpaca PAPER smoke test", [sys.executable, "scripts/alpaca_smoke_test.py"]),
    ("Local CPU embedding smoke test", [sys.executable, "scripts/local_embedding_smoke_test.py"]),
]


def main():
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        subprocess.run(cmd, check=True)
    print("\nCATS V2ET external run preflight: PASS")


if __name__ == "__main__":
    main()
