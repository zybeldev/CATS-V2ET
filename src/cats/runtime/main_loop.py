from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time
from typing import Callable, Iterable

from cats.services.tss import TradingSignalService


MANUAL_TRIGGER_ONLY = "MANUAL_TRIGGER_ONLY"
AUTO_PAPER_EXECUTION = "AUTO_PAPER_EXECUTION"
ACTIVATION_MODES = {MANUAL_TRIGGER_ONLY, AUTO_PAPER_EXECUTION}


@dataclass(frozen=True)
class MainLoopConfig:
    market_interval_seconds: float = 60.0
    news_interval_seconds: float = 3600.0
    taa_interval_seconds: float = 300.0
    auto_execution_interval_seconds: float = 600.0
    market_lookback_days: int = 90
    news_lookback_minutes: int = 120
    additional_symbols: tuple[str, ...] = ()
    selected_symbols_only: bool = False
    activation_mode: str = MANUAL_TRIGGER_ONLY

    def __post_init__(self) -> None:
        if self.market_interval_seconds <= 0:
            raise ValueError("market_interval_seconds must be positive")
        if self.news_interval_seconds <= 0:
            raise ValueError("news_interval_seconds must be positive")
        if self.taa_interval_seconds <= 0:
            raise ValueError("taa_interval_seconds must be positive")
        if self.auto_execution_interval_seconds <= 0:
            raise ValueError("auto_execution_interval_seconds must be positive")
        if self.activation_mode not in ACTIVATION_MODES:
            raise ValueError(f"activation_mode must be one of {sorted(ACTIVATION_MODES)}")
        if self.market_lookback_days <= 0:
            raise ValueError("market_lookback_days must be positive")
        if self.news_lookback_minutes <= 0:
            raise ValueError("news_lookback_minutes must be positive")


@dataclass(frozen=True)
class MainLoopCycleResult:
    observed_at: datetime
    symbols: tuple[str, ...]
    market: tuple[dict, ...]
    news: tuple[dict, ...]
    assessments: tuple[dict, ...]
    account: dict
    auto_execution: dict | None = None


class JsonMainLoopStatusStore:
    """Small operational status projection for the Streamlit console.

    This is runtime observability only. It is not authoritative portfolio state and
    it does not participate in CATS reasoning, validation, or execution authority.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def _json_default(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, indent=2, default=self._json_default, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temp, self.path)


class CatsMainOperatingLoop:
    """Continuous CATS observation/TAA loop with optional PAPER-cycle activation.

    Monitoring remains observational. When AUTO_PAPER_EXECUTION is explicitly
    enabled, this loop may *trigger* the already-existing full CATS PAPER launcher
    after a fresh FINAL TAA monitoring assessment and the configured cooldown.
    The triggered flow still preserves the existing authority chain:
    TAA -> PMA -> PMS when required -> SYS -> TEA -> TES -> Alpaca PAPER.
    This loop does not originate portfolio intent or bypass validation.
    """

    def __init__(
        self,
        *,
        broker,
        market_data,
        news_source,
        status_store: JsonMainLoopStatusStore,
        config: MainLoopConfig | None = None,
        tss: TradingSignalService | None = None,
        assessment_service=None,
        execution_runner=None,
        startup_recovery: dict | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.broker = broker
        self.market_data = market_data
        self.news_source = news_source
        self.status_store = status_store
        self.config = config or MainLoopConfig()
        self.tss = tss or TradingSignalService()
        self.assessment_service = assessment_service
        self.execution_runner = execution_runner
        self.startup_recovery = startup_recovery or {"status": "NOT_RUN"}
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.started_at: datetime | None = None
        self.cycle_count = 0
        self.last_market_cycle_at: datetime | None = None
        self.last_news_check_at: datetime | None = None
        self.last_taa_assessment_at: datetime | None = None
        self.latest_news: tuple[dict, ...] = ()
        self.latest_news_items: tuple = ()
        self.latest_market: tuple[dict, ...] = ()
        self.latest_assessments: tuple[dict, ...] = ()
        self.latest_symbols: tuple[str, ...] = ()
        self.news_status: str = "NOT_CHECKED"
        self._latest_news_signature: tuple | None = None
        self.last_error: str | None = None
        self.last_taa_error: str | None = None
        self.last_auto_execution_at: datetime | None = None
        self.last_auto_execution_state: str | None = None
        self.last_auto_execution_error: str | None = None
        self.last_auto_execution_symbol: str | None = None
        self.last_auto_execution_evidence_url: str | None = None
        self.last_auto_execution_detail: str | None = None

    @staticmethod
    def _clean_symbols(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted({str(value).strip().upper() for value in values if str(value).strip()}))

    def _universe(self, positions) -> tuple[str, ...]:
        selected = self._clean_symbols(self.config.additional_symbols)
        if self.config.selected_symbols_only and selected:
            return selected
        held = [getattr(position, "symbol", "") for position in positions]
        return self._clean_symbols((*held, *selected))

    def _market_snapshot(self, symbols: tuple[str, ...]) -> tuple[dict, ...]:
        rows: list[dict] = []
        for symbol in symbols:
            latest_price = None
            latest_trade_at = None
            try:
                latest = self.market_data.get_latest_trade(symbol)
                if latest is not None:
                    latest_price = float(latest[0])
                    latest_trade_at = latest[1]
            except Exception:
                # Daily TSS measurements still provide a usable surveillance state
                # if the latest-trade endpoint is temporarily unavailable.
                latest_price = None
                latest_trade_at = None

            bars = self.market_data.get_daily_bars(
                symbol,
                lookback_days=self.config.market_lookback_days,
            )
            measurements = self.tss.calculate_equity_measurements(bars)
            rows.append(
                {
                    "symbol": symbol,
                    "latest_trade_price": latest_price,
                    "latest_trade_at": latest_trade_at,
                    "tss_last_price": measurements.last_price,
                    "return_1_period": measurements.return_1_period,
                    "sma_short": measurements.sma_short,
                    "sma_long": measurements.sma_long,
                    "momentum": measurements.momentum,
                    "annualized_volatility": measurements.annualized_volatility,
                    "average_volume": measurements.average_volume,
                    "liquidity_proxy": measurements.liquidity_proxy,
                }
            )
        return tuple(rows)

    @staticmethod
    def _news_snapshot(items) -> tuple[dict, ...]:
        return tuple(
            {
                "news_id": item.news_id,
                "headline": item.headline,
                "source": item.source,
                "url": item.url,
                "summary": item.summary,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "symbols": list(item.symbols),
                "author": item.author,
            }
            for item in items
        )

    def _news_due(self, now: datetime, *, force: bool = False) -> bool:
        if force or self.last_news_check_at is None:
            return True
        return (now - self.last_news_check_at).total_seconds() >= self.config.news_interval_seconds

    def _taa_due(self, now: datetime, *, force: bool = False) -> bool:
        if self.assessment_service is None:
            return False
        if force or self.last_taa_assessment_at is None:
            return True
        return (now - self.last_taa_assessment_at).total_seconds() >= self.config.taa_interval_seconds

    def _auto_execution_due(self, now: datetime) -> bool:
        if self.config.activation_mode != AUTO_PAPER_EXECUTION:
            return False
        if self.execution_runner is None:
            return False
        if self.last_auto_execution_at is None:
            return True
        return (
            now - self.last_auto_execution_at
        ).total_seconds() >= self.config.auto_execution_interval_seconds

    def _selected_auto_symbol(self) -> str | None:
        # V2ET auto execution is intentionally bounded to the explicitly selected
        # operator instrument, not every held position that appears in surveillance.
        values = self._clean_symbols(self.config.additional_symbols)
        return values[0] if values else None

    def _auto_evidence_url(self, symbol: str) -> str | None:
        symbol = symbol.upper()
        for item in self.latest_news:
            url = str(item.get("url") or "").strip()
            symbols = {str(value).upper() for value in (item.get("symbols") or [])}
            if url and (not symbols or symbol in symbols):
                return url
        return None

    def _run_auto_execution(self, now: datetime) -> dict:
        symbol = self._selected_auto_symbol()
        self.last_auto_execution_at = now
        self.last_auto_execution_symbol = symbol
        self.last_auto_execution_error = None
        self.last_auto_execution_detail = None

        if not symbol:
            self.last_auto_execution_state = "SKIPPED_NO_SYMBOL"
            return {"status": self.last_auto_execution_state}

        evidence_url = self._auto_evidence_url(symbol)
        self.last_auto_execution_evidence_url = evidence_url
        if not evidence_url:
            self.last_auto_execution_state = "SKIPPED_NO_EVIDENCE"
            return {"status": self.last_auto_execution_state, "symbol": symbol}

        self.last_auto_execution_state = "RUNNING"
        # Publish before the synchronous full flow starts so the UI can show that
        # the authority chain is currently active.
        self._publish("RUNNING")
        try:
            result = self.execution_runner(symbol=symbol, evidence_url=evidence_url)
            result = result if isinstance(result, dict) else {"status": "COMPLETED", "detail": str(result)}
            self.last_auto_execution_state = str(result.get("status") or "COMPLETED")
            detail = result.get("detail")
            self.last_auto_execution_detail = None if detail is None else str(detail)
            self.last_auto_execution_at = self.clock()
            return {"symbol": symbol, "evidence_url": evidence_url, **result}
        except Exception as exc:
            self.last_auto_execution_state = "ERROR"
            self.last_auto_execution_error = f"{type(exc).__name__}: {exc}"
            self.last_auto_execution_at = self.clock()
            return {
                "status": "ERROR",
                "symbol": symbol,
                "evidence_url": evidence_url,
                "detail": self.last_auto_execution_error,
            }

    def _assessment_snapshot(self, market: tuple[dict, ...]) -> tuple[dict, ...]:
        if self.assessment_service is None:
            return ()
        rows: list[dict] = []
        errors: list[str] = []
        for market_row in market:
            symbol = str(market_row.get("symbol") or "").upper()
            if not symbol:
                continue
            try:
                rows.append(
                    self.assessment_service.assess(
                        symbol=symbol,
                        market_row=market_row,
                        news_items=self.latest_news_items,
                    )
                )
            except Exception as exc:
                errors.append(f"{symbol}: {type(exc).__name__}: {exc}")
                rows.append(
                    {
                        "status": "ERROR",
                        "mode": "MONITORING_ONLY",
                        "symbol": symbol,
                        "summary": f"TAA monitoring assessment failed: {type(exc).__name__}: {exc}",
                    }
                )
        self.last_taa_error = "; ".join(errors) if errors else None
        return tuple(rows)

    def run_cycle(self, *, force_news: bool = False, force_taa: bool = False) -> MainLoopCycleResult:
        now = self.clock()
        account = self.broker.get_account()
        positions = self.broker.get_positions()
        symbols = self._universe(positions)
        market = self._market_snapshot(symbols)
        self.last_market_cycle_at = now
        self.latest_market = market
        self.latest_symbols = symbols

        if self._news_due(now, force=force_news):
            start = now - timedelta(minutes=self.config.news_lookback_minutes)
            items = self.news_source.get_news(symbols, start=start, limit=50) if symbols else []
            self.latest_news_items = tuple(items)
            next_news = self._news_snapshot(items)
            next_signature = tuple(sorted(
                (str(row.get("news_id") or ""), str(row.get("updated_at") or row.get("created_at") or ""))
                for row in next_news
            ))
            if not next_news:
                self.news_status = "NO_NEWS"
            elif self._latest_news_signature is None:
                self.news_status = "INITIAL"
            elif next_signature == self._latest_news_signature:
                self.news_status = "UNCHANGED"
            else:
                self.news_status = "NEW"
            self._latest_news_signature = next_signature
            self.latest_news = next_news
            self.last_news_check_at = now

        taa_ran = False
        if self._taa_due(now, force=force_taa):
            self.latest_assessments = self._assessment_snapshot(market)
            # Record completion, not inference-start time, so operator chronology
            # matches the persisted TAA assessment timestamp semantics.
            self.last_taa_assessment_at = self.clock()
            taa_ran = True

        auto_execution = None
        has_final_assessment = any(
            str(row.get("status") or "").upper() == "FINAL"
            for row in self.latest_assessments
        )
        if taa_ran and has_final_assessment and self._auto_execution_due(now):
            auto_execution = self._run_auto_execution(now)

        self.cycle_count += 1
        self.last_error = None
        result = MainLoopCycleResult(
            observed_at=now,
            symbols=symbols,
            market=self.latest_market,
            news=self.latest_news,
            assessments=self.latest_assessments,
            account={
                "cash": float(account.cash),
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "position_count": len(positions),
            },
            auto_execution=auto_execution,
        )
        self._publish("RUNNING", result=result)
        return result

    def _publish(self, status: str, *, result: MainLoopCycleResult | None = None) -> None:
        payload = {
            "status": status,
            "mode": "MONITORING",
            "pid": os.getpid(),
            "started_at": self.started_at,
            "heartbeat_at": self.clock(),
            "cycle_count": self.cycle_count,
            "market_interval_seconds": self.config.market_interval_seconds,
            "news_interval_seconds": self.config.news_interval_seconds,
            "taa_interval_seconds": self.config.taa_interval_seconds,
            "last_market_cycle_at": self.last_market_cycle_at,
            "last_news_check_at": self.last_news_check_at,
            "news_status": self.news_status,
            "last_taa_assessment_at": self.last_taa_assessment_at,
            "symbols": list(self.latest_symbols),
            "market": list(self.latest_market),
            "news": list(self.latest_news),
            "assessments": list(self.latest_assessments),
            "last_error": self.last_error,
            "last_taa_error": self.last_taa_error,
            "interpretation": "TAA_MONITORING" if self.assessment_service is not None else "DISABLED",
            "authority_chain": self.config.activation_mode,
            "auto_execution_interval_seconds": self.config.auto_execution_interval_seconds,
            "last_auto_execution_at": self.last_auto_execution_at,
            "last_auto_execution_state": self.last_auto_execution_state,
            "last_auto_execution_error": self.last_auto_execution_error,
            "last_auto_execution_symbol": self.last_auto_execution_symbol,
            "last_auto_execution_evidence_url": self.last_auto_execution_evidence_url,
            "last_auto_execution_detail": self.last_auto_execution_detail,
            "startup_recovery": self.startup_recovery,
        }
        if result is not None:
            payload["account"] = result.account
        self.status_store.write(payload)

    def run_forever(self, *, should_stop: Callable[[], bool]) -> None:
        self.started_at = self.clock()
        self._publish("STARTING")
        try:
            while not should_stop():
                cycle_started = time.monotonic()
                try:
                    self.run_cycle()
                except Exception as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"
                    self._publish("DEGRADED")
                elapsed = time.monotonic() - cycle_started
                remaining = max(0.0, self.config.market_interval_seconds - elapsed)
                # One-second slices make STOP responsive without introducing a
                # scheduler/threading dependency into the bounded V2ET runtime.
                while remaining > 0 and not should_stop():
                    sleep_for = min(1.0, remaining)
                    time.sleep(sleep_for)
                    remaining -= sleep_for
        finally:
            self._publish("STOPPED")
