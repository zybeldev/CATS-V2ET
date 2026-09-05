from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.database.base import Base
from cats.database import models
from cats.runtime.production_persistence import ProductionFlowPersistence
from cats.retrieval.models import EvidenceDocument


def test_production_persistence_bootstraps_and_persists_evidence():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        p = ProductionFlowPersistence(session)
        flow_id, instrument_id, config_id, envelope_id, portfolio_id, state_id = [uuid4() for _ in range(6)]
        p.bootstrap(
            flow_id=flow_id, instrument_id=instrument_id, symbol="AAPL",
            config_id=config_id, strategic_envelope_id=envelope_id,
            portfolio_id=portfolio_id, portfolio_state_id=state_id,
            cash=9000, equity=10000, buying_power=9000,
        )
        doc = EvidenceDocument(
            text="public evidence",
            source_name="test",
            external_reference="https://example.com",
            financial_instrument_id=instrument_id,
        )
        p.persist_evidence([doc])
        p.complete_flow(flow_id, status="COMPLETED")

        assert session.get(models.TraceFlow, str(flow_id)).status == "COMPLETED"
        assert session.get(models.EvidenceItem, str(doc.evidence_document_id)) is not None


def test_bootstrap_does_not_duplicate_target_instrument_when_already_held():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        p = ProductionFlowPersistence(session)
        flow_id, instrument_id, config_id, envelope_id, portfolio_id, state_id = [uuid4() for _ in range(6)]

        p.bootstrap(
            flow_id=flow_id,
            instrument_id=instrument_id,
            symbol="AAPL",
            config_id=config_id,
            strategic_envelope_id=envelope_id,
            portfolio_id=portfolio_id,
            portfolio_state_id=state_id,
            cash=9000,
            equity=10000,
            buying_power=9000,
            positions=[
                {
                    "financial_instrument_id": instrument_id,
                    "symbol": "AAPL",
                    "quantity": 1.25,
                    "average_cost": 200.0,
                    "market_value": 250.0,
                    "currency": "USD",
                }
            ],
        )

        instruments = session.query(models.FinancialInstrument).all()
        assert len(instruments) == 1
        assert instruments[0].financial_instrument_id == str(instrument_id)
        assert instruments[0].symbol == "AAPL"
