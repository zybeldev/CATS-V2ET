from datetime import datetime, timezone

from cats.adapters.llm import DeterministicAssessmentModel
from cats.adapters.news import AlpacaNewsItem
from cats.runtime.monitoring_assessment import MonitoringAssessmentService


class FakeEmbeddings:
    def embed(self, texts):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append([
                1.0 if "apple" in lower or "aapl" in lower else 0.0,
                1.0 if "market" in lower or "financial" in lower else 0.0,
                1.0,
            ])
        return vectors


def test_monitoring_assessment_uses_existing_taa_contract_without_downstream_authority():
    now = datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc)
    service = MonitoringAssessmentService(
        reasoning_model=DeterministicAssessmentModel(),
        embedding_provider=FakeEmbeddings(),
        clock=lambda: now,
    )
    market = {
        "symbol": "AAPL",
        "tss_last_price": 330.0,
        "return_1_period": 0.01,
        "sma_short": 328.0,
        "sma_long": 320.0,
        "momentum": 0.04,
        "annualized_volatility": 0.31,
        "average_volume": 1_800_000.0,
        "liquidity_proxy": 594_000_000.0,
    }
    news = [
        AlpacaNewsItem(
            news_id="news-1",
            headline="Apple supplier update",
            source="benzinga",
            url="https://example.com/apple",
            summary="Apple supply-chain conditions changed.",
            created_at=now,
            updated_at=now,
            symbols=("AAPL",),
            content="The article contains additional Apple financial context.",
            author="Reporter",
        )
    ]

    result = service.assess(symbol="AAPL", market_row=market, news_items=news)

    assert result["status"] == "FINAL"
    assert result["mode"] == "MONITORING_ONLY"
    assert result["assessment_type"] == "CANDIDATE"
    assert result["horizon"] == "TACTICAL"
    assert result["evidence_items_used"] == 1
    assert "AAPL" in result["summary"]
    assert result["reasoning_metrics"] is None
