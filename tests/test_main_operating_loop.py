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
        assert symbol == "AAPL"
        return (201.25, self.now)

    def get_daily_bars(self, symbol, lookback_days=90):
        assert symbol == "AAPL"
        assert lookback_days == 90
        return [EquityBar(close=180.0 + i, volume=1_000_000 + i) for i in range(25)]


class FakeNews:
    def __init__(self, now):
        self.now = now
        self.calls = 0

    def get_news(self, symbols, *, start=None, limit=50):
        self.calls += 1
        assert tuple(symbols) == ("AAPL",)
        assert limit == 50
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


def test_main_loop_cycle_monitors_market_and_news_and_publishes_status(tmp_path: Path):
    now = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)
    news = FakeNews(now)
    status_path = tmp_path / "status.json"
    loop = CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(now),
        news_source=news,
        status_store=JsonMainLoopStatusStore(status_path),
        config=MainLoopConfig(market_interval_seconds=60, news_interval_seconds=3600),
        clock=lambda: now,
    )
    loop.started_at = now

    result = loop.run_cycle(force_news=True)

    assert result.symbols == ("AAPL",)
    assert result.market[0]["latest_trade_price"] == 201.25
    assert result.news[0]["headline"] == "Apple test headline"
    assert news.calls == 1

    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "RUNNING"
    assert status["mode"] == "MONITORING"
    assert status["cycle_count"] == 1
    assert status["symbols"] == ["AAPL"]
    assert status["authority_chain"] == "MANUAL_TRIGGER_ONLY"


def test_news_refresh_respects_configured_cadence(tmp_path: Path):
    start = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)
    times = iter([start, start, start + timedelta(minutes=1), start + timedelta(minutes=1)])
    news = FakeNews(start)
    loop = CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(start),
        news_source=news,
        status_store=JsonMainLoopStatusStore(tmp_path / "status.json"),
        config=MainLoopConfig(market_interval_seconds=60, news_interval_seconds=3600),
        clock=lambda: next(times),
    )
    loop.started_at = start

    loop.run_cycle(force_news=True)
    loop.run_cycle()

    assert news.calls == 1


class FakeAssessmentService:
    def __init__(self):
        self.calls = 0

    def assess(self, *, symbol, market_row, news_items):
        self.calls += 1
        return {
            "status": "FINAL",
            "mode": "MONITORING_ONLY",
            "symbol": symbol,
            "horizon": "TACTICAL",
            "assessment_type": "CANDIDATE",
            "confidence": 0.7,
            "summary": f"{symbol} monitoring assessment",
            "assessed_at": datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc),
            "valid_until": datetime(2026, 9, 3, 16, 0, tzinfo=timezone.utc),
            "evidence_items_used": len(tuple(news_items)),
            "reasoning_metrics": None,
        }


def test_taa_monitoring_runs_on_first_cycle_and_respects_cadence(tmp_path: Path):
    now = [datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)]
    news = FakeNews(now[0])
    taa = FakeAssessmentService()
    loop = CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(now[0]),
        news_source=news,
        status_store=JsonMainLoopStatusStore(tmp_path / "status.json"),
        config=MainLoopConfig(
            market_interval_seconds=60,
            news_interval_seconds=3600,
            taa_interval_seconds=300,
        ),
        assessment_service=taa,
        clock=lambda: now[0],
    )
    loop.started_at = now[0]

    first = loop.run_cycle(force_news=True)
    now[0] = now[0] + timedelta(minutes=1)
    second = loop.run_cycle()
    now[0] = now[0] + timedelta(minutes=4)
    third = loop.run_cycle()

    assert taa.calls == 2
    assert first.assessments[0]["assessment_type"] == "CANDIDATE"
    assert second.assessments[0]["summary"] == "AAPL monitoring assessment"
    assert third.assessments[0]["mode"] == "MONITORING_ONLY"

    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert status["interpretation"] == "TAA_MONITORING"
    assert status["authority_chain"] == "MANUAL_TRIGGER_ONLY"
    assert status["last_taa_assessment_at"] is not None


def test_selected_symbol_mode_uses_only_requested_instrument(tmp_path: Path):
    now = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)
    loop = CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(now),
        news_source=FakeNews(now),
        status_store=JsonMainLoopStatusStore(tmp_path / "status.json"),
        config=MainLoopConfig(
            additional_symbols=("NVDA",),
            selected_symbols_only=True,
        ),
        clock=lambda: now,
    )

    assert loop._universe([SimpleNamespace(symbol="AAPL")]) == ("NVDA",)


def test_news_status_reports_unchanged_when_refresh_returns_same_items(tmp_path: Path):
    now = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)
    news = FakeNews(now)
    loop = CatsMainOperatingLoop(
        broker=FakeBroker(),
        market_data=FakeMarketData(now),
        news_source=news,
        status_store=JsonMainLoopStatusStore(tmp_path / "status.json"),
        config=MainLoopConfig(market_interval_seconds=60, news_interval_seconds=3600),
        clock=lambda: now,
    )
    loop.started_at = now

    loop.run_cycle(force_news=True)
    first_status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    loop.run_cycle(force_news=True)
    second_status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))

    assert first_status["news_status"] == "INITIAL"
    assert second_status["news_status"] == "UNCHANGED"
