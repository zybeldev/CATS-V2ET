from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys

from cats.adapters.alpaca import AlpacaPaperAdapter
from cats.adapters.embeddings import LocalFastEmbedEmbeddingAdapter
from cats.adapters.llm import RemoteQwenReasoningAdapter
from cats.adapters.market_data import AlpacaMarketDataAdapter
from cats.adapters.news import AlpacaNewsAdapter
from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.runtime.main_loop import (
    AUTO_PAPER_EXECUTION,
    MANUAL_TRIGGER_ONLY,
    CatsMainOperatingLoop,
    JsonMainLoopStatusStore,
    MainLoopConfig,
)
from cats.runtime.monitoring_assessment import MonitoringAssessmentService
from cats.runtime.real_run import require_real_run_ready
from cats.runtime.startup_recovery import recover_outstanding_paper_flows
from cats.ui import CatsUiReadModel, build_paper_command


BLOCKING_FLOW_STATUSES = {"STARTED", "RUNNING", "SUSPENDED", "PENDING", "EXECUTING"}


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    return default if not raw else float(raw)


def _activation_mode() -> str:
    value = (os.getenv("CATS_EXECUTION_ACTIVATION") or MANUAL_TRIGGER_ONLY).strip().upper()
    return value or MANUAL_TRIGGER_ONLY


def _blocking_flow_detail() -> str | None:
    """Fail closed when any persisted PAPER flow still appears unresolved.

    CATS must never create a new flow merely to continue an outstanding execution.
    Recovery/reconciliation of the original flow remains the authoritative path.
    """
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    model = CatsUiReadModel(engine)
    for row in model.latest_flows(limit=20):
        status = str(row.get("status") or "").upper()
        if status in BLOCKING_FLOW_STATUSES:
            flow_id = row.get("flow_id") or row.get("id") or "unknown"
            return f"{status} flow {flow_id} must be resolved/recovered before a new PAPER flow."
    return None


def _auto_execution_runner(project_root: Path, qwen_endpoint: str):
    def run(*, symbol: str, evidence_url: str) -> dict:
        blocked = _blocking_flow_detail()
        if blocked:
            return {"status": "SKIPPED_BLOCKING_FLOW", "detail": blocked}

        command = build_paper_command(
            project_root=project_root,
            symbol=symbol,
            evidence_reference=evidence_url,
            qwen_endpoint_url=qwen_endpoint,
        )
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "detail": "Automatic PAPER evaluation exceeded the 15-minute execution timeout; inspect persisted state before retrying.",
            }

        output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        detail = output[-4000:].strip()
        return {
            "status": "COMPLETED" if completed.returncode == 0 else "FAILED",
            "returncode": completed.returncode,
            "detail": detail,
        }

    return run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the continuous CATS V2ET PAPER market/news/TAA operating loop."
    )
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--status-file", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    status_file = Path(args.status_file)
    stop_file = Path(args.stop_file)
    pid_file = Path(args.pid_file)
    project_root = Path(__file__).resolve().parents[1]
    status_file.parent.mkdir(parents=True, exist_ok=True)

    require_real_run_ready(require_openai=False)

    environment = (os.getenv("CATS_ENVIRONMENT") or "").strip().upper()
    api_key = os.getenv("ALPACA_API_KEY") or os.getenv("CATS_ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET") or os.getenv("CATS_ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Blocked: Alpaca PAPER credentials are required.")

    broker = AlpacaPaperAdapter(api_key, api_secret)
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    Session = create_session_factory(engine)
    with Session() as session:
        startup_recovery = recover_outstanding_paper_flows(session=session, broker=broker)

    if startup_recovery.get("status") == "BLOCKED":
        JsonMainLoopStatusStore(status_file).write(
            {
                "status": "RECOVERY_BLOCKED",
                "mode": "STARTUP_RECOVERY",
                "pid": os.getpid(),
                "startup_recovery": startup_recovery,
                "symbols": [],
                "market": [],
                "news": [],
                "assessments": [],
            }
        )
        raise SystemExit(str(startup_recovery.get("detail") or "Startup recovery blocked normal operation."))

    qwen_endpoint = (os.getenv("QWEN_ENDPOINT_URL") or "").strip()
    qwen_token = (os.getenv("CATS_QWEN_SESSION_TOKEN") or "").strip()
    if not qwen_endpoint or not qwen_token:
        raise SystemExit(
            "Blocked: QWEN_ENDPOINT_URL and CATS_QWEN_SESSION_TOKEN are required for TAA monitoring."
        )

    activation_mode = _activation_mode()
    if activation_mode == AUTO_PAPER_EXECUTION:
        if environment != "PAPER":
            raise SystemExit("Blocked: AUTO_PAPER_EXECUTION is permitted only when CATS_ENVIRONMENT=PAPER.")
        if (os.getenv("CATS_AUTO_PAPER_CONFIRM") or "").strip().upper() != "YES":
            raise SystemExit(
                "Blocked: CATS_AUTO_PAPER_CONFIRM=YES is required for unattended Alpaca PAPER evaluation."
            )
    elif activation_mode != MANUAL_TRIGGER_ONLY:
        raise SystemExit(
            f"Blocked: unsupported CATS_EXECUTION_ACTIVATION={activation_mode!r}."
        )

    env_symbols = [
        item.strip().upper()
        for item in (os.getenv("CATS_MONITOR_SYMBOLS") or "").split(",")
        if item.strip()
    ]
    symbols = tuple(sorted(set([*args.symbol, *env_symbols])))

    config = MainLoopConfig(
        market_interval_seconds=_float_env("CATS_MAIN_LOOP_MARKET_SECONDS", 60.0),
        news_interval_seconds=_float_env("CATS_MAIN_LOOP_NEWS_SECONDS", 3600.0),
        taa_interval_seconds=_float_env("CATS_MAIN_LOOP_TAA_SECONDS", 300.0),
        auto_execution_interval_seconds=_float_env("CATS_AUTO_PAPER_SECONDS", 600.0),
        news_lookback_minutes=int(_float_env("CATS_MAIN_LOOP_NEWS_LOOKBACK_MINUTES", 120.0)),
        additional_symbols=symbols,
        selected_symbols_only=bool(symbols),
        activation_mode=activation_mode,
    )

    stop_file.unlink(missing_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    stop_requested = False

    def request_stop(_signum=None, _frame=None):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    reasoning = RemoteQwenReasoningAdapter(
        endpoint_url=qwen_endpoint,
        session_token=qwen_token,
    )
    assessment_service = MonitoringAssessmentService(
        reasoning_model=reasoning,
        embedding_provider=LocalFastEmbedEmbeddingAdapter(),
    )

    execution_runner = None
    if activation_mode == AUTO_PAPER_EXECUTION:
        execution_runner = _auto_execution_runner(project_root, qwen_endpoint)

    loop = CatsMainOperatingLoop(
        broker=broker,
        market_data=AlpacaMarketDataAdapter(api_key, api_secret),
        news_source=AlpacaNewsAdapter(api_key, api_secret),
        status_store=JsonMainLoopStatusStore(status_file),
        config=config,
        assessment_service=assessment_service,
        execution_runner=execution_runner,
        startup_recovery=startup_recovery,
    )

    try:
        if args.once:
            loop.started_at = loop.clock()
            loop.run_cycle(force_news=True, force_taa=True)
        else:
            loop.run_forever(
                should_stop=lambda: stop_requested or stop_file.exists(),
            )
    finally:
        pid_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
