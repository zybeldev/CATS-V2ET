from __future__ import annotations

import shutil
import subprocess
import sys
import time


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    docker = shutil.which("docker")
    if docker is None:
        raise SystemExit("Docker is not installed or not on PATH.")

    run([docker, "compose", "up", "-d", "postgres"])

    for attempt in range(30):
        result = subprocess.run(
            [docker, "compose", "exec", "-T", "postgres", "pg_isready", "-U", "cats", "-d", "cats_v2e"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Local PostgreSQL: READY")
            return
        time.sleep(2)

    raise SystemExit("PostgreSQL did not become ready in time.")


if __name__ == "__main__":
    main()
