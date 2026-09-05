from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.adapters.alpaca import BrokerAccount, BrokerActionOutcome, BrokerOrder, BrokerPosition
from cats.database import models
from cats.database.base import Base
from cats.retrieval.models import EvidenceDocument
from cats.runtime.production_paper_flow import ProductionPaperFlow, ProductionPaperFlowInput
from cats.runtime.startup_recovery import recover_outstanding_paper_flows
from cats.services.tss import EquityBar


class RecoverableFakeBroker:
    def __init__(self):
        self.submissions = 0
        self.order = None
        self.position = None

    def get_account(self):
        if self.position is None:
            return BrokerAccount(cash=10000, equity=10000, buying_power=10000)
        return BrokerAccount(cash=9000, equity=10000, buying_power=9000)

    def get_positions(self):
        return [] if self.position is None else [self.position]

    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        self.submissions += 1
        self.order = BrokerOrder(
            broker_order_id="B-STARTUP-1",
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="MARKET",
            status="NEW",
            filled_quantity=0.0,
            average_fill_price=None,
        )
        return BrokerActionOutcome("CONFIRMED", self.order)

    def get_order_by_client_order_id(self, client_order_id):
        if self.order is None or self.order.client_order_id != client_order_id:
            return None
        return self.order

    def mark_filled(self):
        quantity = self.order.quantity
        self.order = BrokerOrder(
            broker_order_id=self.order.broker_order_id,
            client_order_id=self.order.client_order_id,
            symbol=self.order.symbol,
            side=self.order.side,
            quantity=quantity,
            order_type=self.order.order_type,
            status="FILLED",
            filled_quantity=quantity,
            average_fill_price=100.0,
        )
        signed = quantity if self.order.side == "BUY" else -quantity
        self.position = BrokerPosition(
            symbol=self.order.symbol,
            quantity=signed,
            market_value=signed * 100.0,
            average_entry_price=100.0,
        )


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


def test_startup_recovery_finishes_existing_filled_paper_order_without_resubmit():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    broker = RecoverableFakeBroker()

    with Session(engine) as session:
        production = ProductionPaperFlow(
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
        initial = production.run(
            ProductionPaperFlowInput(
                symbol="AAPL",
                evidence_urls=("https://example.com/evidence",),
                openai_model="test",
                max_target_weight=0.10,
            )
        )

        assert initial.completed is False
        assert broker.submissions == 1
        flow = session.query(models.TraceFlow).one()
        assert flow.status == "SUSPENDED"

        broker.mark_filled()
        summary = recover_outstanding_paper_flows(session=session, broker=broker)

        assert summary["status"] == "COMPLETED"
        assert summary["checked_flow_count"] == 1
        assert summary["recovered_flow_count"] == 1
        assert summary["unresolved_flow_count"] == 0
        assert summary["flows"][0]["flow_id"] == flow.flow_id
        assert broker.submissions == 1
        assert session.get(models.TraceFlow, flow.flow_id).status == "COMPLETED"
        assert session.query(models.ExecutionResultRecord).count() == 1
        assert session.query(models.FillRecord).count() == 1
        assert session.query(models.PortfolioState).filter_by(status="ACCEPTED").count() == 1


def test_startup_recovery_clear_when_no_nonterminal_paper_flow_exists():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    broker = RecoverableFakeBroker()

    with Session(engine) as session:
        summary = recover_outstanding_paper_flows(session=session, broker=broker)

    assert summary["status"] == "CLEAR"
    assert summary["checked_flow_count"] == 0
