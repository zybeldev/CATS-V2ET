from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

from cats.adapters.news import AlpacaNewsItem
from cats.runtime.main_loop import CatsMainOperatingLoop, JsonMainLoopStatusStore, MainLoopConfig
from cats.services.tss import EquityBar


class FakeBroker:
    def get_account(self):
        return SimpleNamespace(cash=5000.0, equity=10000.0, buying_power=15000.0)

    def get_positions(self):
        return [SimpleNamespace(symbol="AAPL")]


class FakeMarketData:
    def __init__(self, now):
        self.now = now

    def get_latest_trade(self, symbol):
        return (201.25, self.now)

    def get_daily_bars(self, symbol, lookback_days=90):
        return [EquityBar(close=180.0 + i, volume=1_000_000 + i) for i in range(25)]


class FakeNews:
    def __init__(self, now):
        self.now = now

    def get_news(self, symbols, *, start=None, limit=50):
        return [
            AlpacaNewsItem(
                news_id="1",
                headline="Apple test headline",
                source="Benzinga",
                url="https://example.com/apple",
                summary="Test summary",
                created_at=self.now,
                updated_at=self.now,
                symbols=("AAPL",),
                content="Test content",
                author="Reporter",
            )
        ]


class FakeAssessmentService:
    def assess(self, *, symbol, market_row, news_items):
        return {
            "status": "FINAL",
            "mode": "MONITORING_ONLY",
            "symbol": symbol,
            "horizon": "TACTICAL",
            "assessment_type": "CANDIDATE",
            "confidence": 0.7,
            "summary": f"{symbol} monitoring assessment",
            "assessed_at": datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc),
            "valid_until": datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc),
            "evidence_items_used": len(tuple(news_items)),
            "reasoning_metrics": None,
        }


class FakeExecutionRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, *, symbol, evidence_url):
        self.calls.append((symbol, evidence_url))
        return {"status": "COMPLETED", "detail": "paper flow completed"}


def build_loop(tmp_path: Path, current, runner: FakeExecutionRunner) -> CatsMainOperatingLoop:
    return CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(current[0]),
        news_source=FakeNews(current[0]),
        status_store=JsonMainLoopStatusStore(tmp_path / "status.json"),
        config=MainLoopConfig(
            market_interval_seconds=60,
            news_interval_seconds=3600,
            taa_interval_seconds=300,
            auto_execution_interval_seconds=600,
            additional_symbols=("AAPL",),
            activation_mode="AUTO_PAPER_EXECUTION",
        ),
        assessment_service=FakeAssessmentService(),
        execution_runner=runner,
        clock=lambda: current[0],
    )


def test_auto_paper_execution_triggers_existing_full_flow_after_final_taa(tmp_path: Path):
    current = [datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc)]
    runner = FakeExecutionRunner()
    loop = build_loop(tmp_path, current, runner)
    loop.started_at = current[0]

    result = loop.run_cycle(force_news=True, force_taa=True)

    assert runner.calls == [("AAPL", "https://example.com/apple")]
    assert result.auto_execution["status"] == "COMPLETED"
    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert status["authority_chain"] == "AUTO_PAPER_EXECUTION"
    assert status["last_auto_execution_state"] == "COMPLETED"


def test_auto_paper_execution_respects_ten_minute_cooldown(tmp_path: Path):
    current = [datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc)]
    runner = FakeExecutionRunner()
    loop = build_loop(tmp_path, current, runner)
    loop.started_at = current[0]

    loop.run_cycle(force_news=True, force_taa=True)
    current[0] += timedelta(minutes=5)
    loop.run_cycle()
    current[0] += timedelta(minutes=5)
    loop.run_cycle()

    assert runner.calls == [
        ("AAPL", "https://example.com/apple"),
        ("AAPL", "https://example.com/apple"),
    ]


def test_auto_paper_execution_skips_without_monitored_evidence_url(tmp_path: Path):
    current = [datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc)]
    runner = FakeExecutionRunner()
    loop = build_loop(tmp_path, current, runner)
    loop.started_at = current[0]
    loop.latest_news = ({"symbols": ["AAPL"], "url": ""},)
    loop.latest_news_items = ()
    loop.last_news_check_at = current[0]

    result = loop.run_cycle(force_news=False, force_taa=True)

    assert runner.calls == []
    assert result.auto_execution["status"] == "SKIPPED_NO_EVIDENCE"
