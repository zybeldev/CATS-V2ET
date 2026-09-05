from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit
import urllib.error
import urllib.request


@dataclass(frozen=True)
class RuntimePaths:
    directory: Path
    status: Path
    pid: Path
    stop: Path
    log: Path


def runtime_paths(project_root: Path) -> RuntimePaths:
    directory = Path(project_root) / ".cats_runtime"
    return RuntimePaths(
        directory=directory,
        status=directory / "main_loop_status.json",
        pid=directory / "main_loop.pid",
        stop=directory / "main_loop.stop",
        log=directory / "main_loop.log",
    )


def qwen_health_url(endpoint_url: str) -> str:
    parts = urlsplit(endpoint_url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("Qwen endpoint URL is not valid.")
    path = parts.path.rstrip("/")
    if path.endswith("/reason"):
        path = path[: -len("/reason")]
    return urlunsplit((parts.scheme, parts.netloc, path + "/health", "", ""))


def probe_qwen_health(endpoint_url: str, session_token: str, *, timeout_seconds: float = 8.0) -> dict[str, Any]:
    if not endpoint_url.strip() or not session_token.strip():
        return {"ready": False, "detail": "Qwen endpoint/token not configured."}
    request = urllib.request.Request(
        qwen_health_url(endpoint_url),
        headers={"Accept": "application/json", "X-CATS-Session": session_token.strip()},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
        payload = json.loads(body)
        if isinstance(payload, dict) and payload.get("status") == "ok":
            return {"ready": True, "detail": payload.get("model") or "Qwen endpoint reachable."}
        return {"ready": False, "detail": "Qwen health endpoint returned an unexpected response."}
    except urllib.error.HTTPError as exc:
        return {"ready": False, "detail": f"Qwen health check returned HTTP {exc.code}."}
    except urllib.error.URLError as exc:
        return {"ready": False, "detail": f"Qwen endpoint unreachable: {exc.reason}"}
    except Exception as exc:
        return {"ready": False, "detail": f"Qwen health check failed: {type(exc).__name__}: {exc}"}


def read_main_loop_status(project_root: Path) -> dict[str, Any]:
    path = runtime_paths(project_root).status
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def read_main_loop_pid(project_root: Path) -> int | None:
    path = runtime_paths(project_root).pid
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def pid_is_running(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main_loop_is_running(project_root: Path) -> bool:
    return pid_is_running(read_main_loop_pid(project_root))


def build_main_loop_command(project_root: Path) -> list[str]:
    paths = runtime_paths(project_root)
    return [
        sys.executable,
        str(Path(project_root) / "scripts" / "cats_main_loop.py"),
        "--status-file",
        str(paths.status),
        "--stop-file",
        str(paths.stop),
        "--pid-file",
        str(paths.pid),
    ]


def start_main_loop(project_root: Path, *, env: dict[str, str] | None = None) -> int:
    paths = runtime_paths(project_root)
    paths.directory.mkdir(parents=True, exist_ok=True)
    if main_loop_is_running(project_root):
        raise RuntimeError("CATS main operating loop is already running.")
    paths.stop.unlink(missing_ok=True)
    log_handle = paths.log.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            build_main_loop_command(project_root),
            cwd=project_root,
            env=dict(os.environ if env is None else env),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    finally:
        log_handle.close()
    paths.pid.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def stop_main_loop(project_root: Path) -> bool:
    paths = runtime_paths(project_root)
    paths.directory.mkdir(parents=True, exist_ok=True)
    paths.stop.write_text("stop\n", encoding="utf-8")
    pid = read_main_loop_pid(project_root)
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


def tail_runtime_log(project_root: Path, *, max_chars: int = 8000) -> str:
    path = runtime_paths(project_root).log
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def describe_launcher_failure(output: str, returncode: int) -> str:
    text = output or ""
    if "Remote Qwen endpoint is unavailable" in text or "Name or service not known" in text:
        return (
            "CATS PAPER run failed because the remote Qwen endpoint is unavailable. "
            "Restart/update the Colab Qwen endpoint and load CATS again before retrying."
        )
    if "HTTP Error 403" in text or "HTTP 403" in text:
        return (
            "CATS PAPER run failed because the evidence website refused automated access (HTTP 403). "
            "Use a permitted public source or the Local File evidence path."
        )
    if "CATS_QWEN_SESSION_TOKEN" in text and "Blocked" in text:
        return "CATS PAPER run is blocked because the Qwen session token is not loaded."
    return f"CATS PAPER run failed (exit code {returncode}). Open the technical output below for details."
