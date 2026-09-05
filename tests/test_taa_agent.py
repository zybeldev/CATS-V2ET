from uuid import uuid4

from cats.adapters.llm.testing import DeterministicAssessmentModel
from cats.agents.taa import TradingAssessmentAgent
from cats.retrieval import EvidenceDocument, InMemoryVectorStore, RetrievalService
from cats.retrieval.testing import DeterministicHashEmbeddingProvider
from cats.services.tss import EquityBar, TradingSignalService


def test_taa_builds_grounded_structured_assessment():
    instrument_id = uuid4()
    retrieval = RetrievalService(DeterministicHashEmbeddingProvider(), InMemoryVectorStore())
    retrieval.index([
        EvidenceDocument(
            text="Company reported stronger revenue growth and improved operating margin.",
            source_name="Public Earnings Release",
            external_reference="https://example.test/release",
            financial_instrument_id=instrument_id,
        ),
        EvidenceDocument(
            text="Management maintained full-year guidance.",
            source_name="Public Investor Update",
            external_reference="https://example.test/update",
            financial_instrument_id=instrument_id,
        ),
    ])
    bars = [EquityBar(close=100+i, volume=1_000_000+i*1000) for i in range(25)]
    measurements = TradingSignalService().calculate_equity_measurements(bars)

    agent = TradingAssessmentAgent(
        retrieval=retrieval,
        reasoning_model=DeterministicAssessmentModel(),
    )
    assessment = agent.assess_equity(
        flow_id=uuid4(),
        financial_instrument_id=instrument_id,
        symbol="ACME",
        horizon="TACTICAL",
        assessment_type="CANDIDATE",
        query_text="revenue growth guidance operating margin",
        tss_measurements=measurements,
        tss_measurement_set_id=uuid4(),
        configuration_version_id=uuid4(),
        top_k=2,
    )

    assert assessment.source == "TAA"
    assert assessment.destination == "PMA"
    assert assessment.assessment_type == "CANDIDATE"
    assert assessment.evidence_item_ids
    assert assessment.tss_measurement_set_ids
    assert "ACME" in assessment.summary
    assert assessment.confidence is not None


def test_taa_cannot_return_portfolio_or_execution_contract():
    assert not hasattr(TradingAssessmentAgent, "execute")
    assert not hasattr(TradingAssessmentAgent, "submit_order")
    assert not hasattr(TradingAssessmentAgent, "issue_portfolio_decision")


def test_taa_exposes_source_age_and_requires_freshness_review():
    from datetime import datetime, timedelta, timezone

    class CapturingReasoningModel:
        def __init__(self):
            self.task = None
            self.context = None

        def reason(self, *, task, context):
            self.task = task
            self.context = context
            return {
                "summary": "Evidence freshness was considered for ACME.",
                "confidence": 0.7,
                "valid_for_minutes": 30,
            }

    instrument_id = uuid4()
    retrieval = RetrievalService(DeterministicHashEmbeddingProvider(), InMemoryVectorStore())
    retrieval.index([
        EvidenceDocument(
            text="Recent company-specific evidence.",
            source_name="Public News",
            external_reference="https://example.test/news",
            financial_instrument_id=instrument_id,
            observed_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
    ])
    bars = [EquityBar(close=100+i, volume=1_000_000) for i in range(25)]
    measurements = TradingSignalService().calculate_equity_measurements(bars)
    reasoning = CapturingReasoningModel()

    agent = TradingAssessmentAgent(retrieval=retrieval, reasoning_model=reasoning)
    agent.assess_equity(
        flow_id=uuid4(),
        financial_instrument_id=instrument_id,
        symbol="ACME",
        horizon="TACTICAL",
        assessment_type="TACTICAL",
        query_text="current evidence",
        tss_measurements=measurements,
        top_k=1,
    )

    evidence = reasoning.context["retrieved_evidence"][0]
    assert evidence["source_date"] is not None
    assert 1.0 < evidence["source_age_days"] < 3.0
    assert evidence["freshness_status"] == "RECENT_7D"
    assert reasoning.context["boundary_rules"]["source_freshness_must_be_evaluated"] is True
    assert "source_date" in reasoning.task
    assert "TACTICAL" in reasoning.task
