from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from cats.agents.taa import TradingAssessmentAgent
from cats.retrieval import InMemoryVectorStore, RetrievalService
from cats.retrieval.models import EvidenceDocument
from cats.runtime.production_paper_flow import instrument_id_for_symbol
from cats.services.tss import EquityMeasurements


@dataclass(frozen=True)
class MonitoringAssessmentConfig:
    horizon: str = "TACTICAL"
    assessment_type: str = "CANDIDATE"
    top_k: int = 5
    max_news_documents: int = 10
    max_chars_per_document: int = 3000

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.max_news_documents <= 0:
            raise ValueError("max_news_documents must be positive")
        if self.max_chars_per_document <= 0:
            raise ValueError("max_chars_per_document must be positive")


class MonitoringAssessmentService:
    """Monitoring-only TAA interpretation for the CATS main operating loop.

    This service deliberately stops at the existing TAA Assessment contract. It
    does not invoke PMA, PMS, SYS, TEA, TES, or the broker execution boundary.
    The resulting assessment is an operational observation published to the UI.
    """

    def __init__(
        self,
        *,
        reasoning_model,
        embedding_provider,
        config: MonitoringAssessmentConfig | None = None,
        clock=None,
    ) -> None:
        self.reasoning_model = reasoning_model
        self.embedding_provider = embedding_provider
        self.config = config or MonitoringAssessmentConfig()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _measurements(market_row: dict) -> EquityMeasurements:
        return EquityMeasurements(
            last_price=float(market_row["tss_last_price"]),
            return_1_period=market_row.get("return_1_period"),
            sma_short=market_row.get("sma_short"),
            sma_long=market_row.get("sma_long"),
            momentum=market_row.get("momentum"),
            annualized_volatility=market_row.get("annualized_volatility"),
            average_volume=market_row.get("average_volume"),
            liquidity_proxy=market_row.get("liquidity_proxy"),
        )

    def _news_documents(self, symbol: str, news_items: Iterable) -> list[EvidenceDocument]:
        instrument_id = instrument_id_for_symbol(symbol)
        documents: list[EvidenceDocument] = []
        for item in news_items:
            item_symbols = tuple(str(value).upper() for value in (getattr(item, "symbols", ()) or ()))
            if item_symbols and symbol not in item_symbols:
                continue

            headline = str(getattr(item, "headline", "") or "").strip()
            summary = str(getattr(item, "summary", "") or "").strip()
            content = str(getattr(item, "content", "") or "").strip()
            parts = [part for part in (headline, summary, content) if part]
            text = "\n\n".join(parts).strip()
            if not text:
                continue
            text = text[: self.config.max_chars_per_document]

            news_id = str(getattr(item, "news_id", "") or "").strip()
            url = getattr(item, "url", None)
            source = str(getattr(item, "source", "") or "Alpaca News").strip()
            created_at = getattr(item, "created_at", None)
            documents.append(
                EvidenceDocument(
                    text=text,
                    source_name=source,
                    external_reference=(str(url) if url else f"alpaca-news:{news_id or 'unknown'}"),
                    financial_instrument_id=instrument_id,
                    observed_at=created_at,
                    retrieved_at=self.clock(),
                    metadata={
                        "source_type": "ALPACA_NEWS",
                        "news_id": news_id,
                        "headline": headline,
                        "symbols": list(item_symbols),
                        "author": getattr(item, "author", None),
                    },
                )
            )
            if len(documents) >= self.config.max_news_documents:
                break
        return documents

    def assess(self, *, symbol: str, market_row: dict, news_items: Iterable) -> dict:
        symbol = symbol.strip().upper()
        instrument_id = instrument_id_for_symbol(symbol)
        retrieval = RetrievalService(self.embedding_provider, InMemoryVectorStore())
        documents = self._news_documents(symbol, news_items)
        retrieval.index(documents)

        taa = TradingAssessmentAgent(
            retrieval=retrieval,
            reasoning_model=self.reasoning_model,
        )
        assessment = taa.assess_equity(
            flow_id=uuid4(),
            financial_instrument_id=instrument_id,
            symbol=symbol,
            horizon=self.config.horizon,
            assessment_type=self.config.assessment_type,
            query_text=f"Current material financial evidence and market conditions for {symbol}",
            tss_measurements=self._measurements(market_row),
            top_k=self.config.top_k,
        )
        assessed_at = self.clock()

        metrics = getattr(self.reasoning_model, "last_metrics", None)
        return {
            "status": assessment.status,
            "mode": "MONITORING_ONLY",
            "symbol": symbol,
            "assessment_id": str(assessment.assessment_id),
            "horizon": assessment.horizon,
            "assessment_type": assessment.assessment_type,
            "confidence": assessment.confidence,
            "summary": assessment.summary,
            "assessed_at": assessed_at,
            "valid_until": assessment.valid_until,
            "evidence_items_used": len(assessment.evidence_item_ids),
            "retrieved_evidence": [
                {
                    "rank": item.rank,
                    "relevance_score": item.score,
                    "source": item.document.source_name,
                    "external_reference": item.document.external_reference,
                    "source_date": item.document.observed_at,
                    "headline": item.document.metadata.get("headline"),
                }
                for item in taa.last_retrieved_evidence
            ],
            "reasoning_metrics": (
                None
                if metrics is None
                else {
                    "transport_seconds": getattr(metrics, "transport_seconds", None),
                    "input_tokens": getattr(metrics, "input_tokens", None),
                    "output_tokens": getattr(metrics, "output_tokens", None),
                    "inference_seconds": getattr(metrics, "inference_seconds", None),
                    "thinking_enabled": getattr(metrics, "thinking_enabled", None),
                }
            ),
        }
