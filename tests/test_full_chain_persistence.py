from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.adapters.alpaca.models import BrokerAccount, BrokerActionOutcome, BrokerOrder, BrokerPosition
from cats.database.base import Base
from cats.database import models
from cats.retrieval.models import EvidenceDocument
from cats.runtime.production_paper_flow import ProductionPaperFlow, ProductionPaperFlowInput
from cats.services.tss import EquityBar


class FakeBroker:
    def __init__(self):
        self.order = None
        self.position = None

    def get_account(self):
        if self.position is None:
            return BrokerAccount(cash=10000, equity=10000, buying_power=10000)
        return BrokerAccount(cash=9000, equity=10000, buying_power=9000)

    def get_positions(self):
        return [] if self.position is None else [self.position]

    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        self.order = BrokerOrder(
            broker_order_id="B1",
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="MARKET",
            status="FILLED",
            filled_quantity=quantity,
            average_fill_price=100.0,
        )
        signed = quantity if side == "BUY" else -quantity
        self.position = BrokerPosition(
            symbol=symbol,
            quantity=signed,
            market_value=signed * 100.0,
            average_entry_price=100.0,
        )
        return BrokerActionOutcome("CONFIRMED", self.order)

    def get_order_by_client_order_id(self, client_order_id):
        return self.order


class FakeMarketData:
    def get_daily_bars(self, symbol, lookback_days=90):
        return [EquityBar(close=100 + i * 0.1, volume=1_000_000) for i in range(30)]


class FakeEmbeddings:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeReasoning:
    def reason(self, *, task, context):
        return {
            "summary": "positive attractive opportunity supported by retrieved evidence",
            "confidence": 0.8,
            "valid_for_minutes": 60,
        }


class FakeEvidenceSource:
    def ingest(self, request):
        return EvidenceDocument(
            text="Public financial evidence supports the assessment.",
            source_name=request.source_name,
            external_reference=request.url,
            financial_instrument_id=request.financial_instrument_id,
        )


def test_complete_evidence_to_broker_to_portfolio_state_chain_is_persisted():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        flow = ProductionPaperFlow(
            alpaca_api_key="x",
            alpaca_api_secret="y",
            openai_api_key="z",
            openai_model="test",
            session=session,
            broker=FakeBroker(),
            market_data=FakeMarketData(),
            reasoning=FakeReasoning(),
            embeddings=FakeEmbeddings(),
            evidence_source=FakeEvidenceSource(),
        )
        result = flow.run(
            ProductionPaperFlowInput(
                symbol="AAPL",
                evidence_urls=("https://example.com/evidence",),
                openai_model="test",
                max_target_weight=0.10,
            )
        )

        assert result.completed is True
        assert result.accepted_portfolio_state_id is not None

        assert session.query(models.EvidenceItem).count() == 1
        assert session.query(models.AssessmentRecord).count() == 1
        assert session.query(models.AssessmentEvidenceLinkRecord).count() == 1
        assert session.query(models.OptimizationRequestRecord).count() == 1
        assert session.query(models.PortfolioAlternativeRecord).count() == 1
        assert session.query(models.PortfolioDecisionRecord).count() == 1
        assert session.query(models.ValidationResultRecord).count() == 1
        assert session.query(models.ExecutionRecord).count() == 1
        assert session.query(models.OrderRecord).count() == 1
        assert session.query(models.FillRecord).count() == 1
        assert session.query(models.ReconciliationRecord).count() == 1
        assert session.query(models.ExecutionResultRecord).count() == 1

        accepted = session.get(models.PortfolioState, str(result.accepted_portfolio_state_id))
        assert accepted.status == "ACCEPTED"
        assert accepted.source_portfolio_decision_id == str(result.portfolio_decision_id)

        trace_types = {r.event_type for r in session.query(models.TraceEventRecord).all()}
        assert "FLOW_STARTED" in trace_types
        assert "EXECUTION_STARTED" in trace_types
        assert "EXECUTION_FINISHED" in trace_types

        assert session.query(models.TraceProvenanceLinkRecord).count() >= 1
        assert session.query(models.TraceLineageLinkRecord).count() >= 3

        flow_row = session.query(models.TraceFlow).one()
        assert flow_row.status == "COMPLETED"


def test_visibility_classifies_pma_intent_from_selected_target_direction():
    class ExistingPositionBroker(FakeBroker):
        def __init__(self):
            super().__init__()
            self.position = BrokerPosition(
                symbol="AAPL",
                quantity=20.0,
                market_value=2000.0,
                average_entry_price=90.0,
            )

        def get_account(self):
            return BrokerAccount(cash=8000, equity=10000, buying_power=8000)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        flow = ProductionPaperFlow(
            alpaca_api_key="x",
            alpaca_api_secret="y",
            openai_api_key="z",
            openai_model="test",
            session=session,
            broker=ExistingPositionBroker(),
            market_data=FakeMarketData(),
            reasoning=FakeReasoning(),
            embeddings=FakeEmbeddings(),
            evidence_source=FakeEvidenceSource(),
        )
        result = flow.run(
            ProductionPaperFlowInput(
                symbol="AAPL",
                evidence_urls=("https://example.com/evidence",),
                openai_model="test",
                max_target_weight=0.10,
            )
        )

        pma_stage = next(
            stage
            for stage in result.visibility_report.as_dict()["stages"]
            if stage["name"] == "PMA DECISION"
        )
        assert pma_stage["details"]["decision_type"] == "SELL_OR_REDUCE"
        assert pma_stage["details"]["required_quantity_delta"] < 0
        assert pma_stage["details"]["semantic_consistency"] == "CONSISTENT"


def test_flow_executes_no_order_when_current_position_is_within_tea_tolerance():
    class WithinToleranceBroker(FakeBroker):
        def __init__(self):
            super().__init__()
            self.position = BrokerPosition(
                symbol="AAPL",
                quantity=1002.0 / 102.9,
                market_value=1002.0,
                average_entry_price=90.0,
            )

        def get_account(self):
            return BrokerAccount(cash=8998, equity=10000, buying_power=8998)

    broker = WithinToleranceBroker()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        flow = ProductionPaperFlow(
            alpaca_api_key="x",
            alpaca_api_secret="y",
            openai_api_key="z",
            openai_model="test",
            session=session,
            broker=broker,
            market_data=FakeMarketData(),
            reasoning=FakeReasoning(),
            embeddings=FakeEmbeddings(),
            evidence_source=FakeEvidenceSource(),
        )
        result = flow.run(
            ProductionPaperFlowInput(
                symbol="AAPL",
                evidence_urls=("https://example.com/evidence",),
                openai_model="test",
                max_target_weight=0.10,
            )
        )

        assert result.completed is True
        assert result.execution_ids == ()
        assert result.accepted_portfolio_state_id is None
        assert broker.order is None
        assert session.query(models.ExecutionRecord).count() == 0
        assert session.query(models.OrderRecord).count() == 0

        report = result.visibility_report.as_dict()
        tea_stage = next(stage for stage in report["stages"] if stage["name"] == "TEA EXECUTION")
        assert tea_stage["status"] == "TARGET_ALREADY_SATISFIED"
        assert report["outcome"] == "COMPLETED_TARGET_ALREADY_SATISFIED"
