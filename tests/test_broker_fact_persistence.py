from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.adapters.alpaca.models import BrokerOrder
from cats.agents.tea import ExecutionRuntimeState
from cats.database.base import Base
from cats.database import models
from cats.repositories import BrokerFactRepository
from cats.runtime.sql_store import SQLExecutionStateStore


def seed(session, decision_id, instrument_id, environment_id, flow_id):
    now = datetime.now(timezone.utc)
    config_id, portfolio_id, capital_id, state_id, envelope_id = [uuid4() for _ in range(5)]
    session.add(models.Environment(environment_id=str(environment_id), environment_code="PAPER", name="Paper", is_active=True))
    session.add(models.FinancialInstrument(financial_instrument_id=str(instrument_id), instrument_type="EQUITY", symbol="AAPL", status="ACTIVE"))
    session.add(models.TraceFlow(flow_id=str(flow_id), environment_id=str(environment_id), flow_type="TEST", started_at=now, status="ACTIVE"))
    session.add(models.ConfigurationVersion(configuration_version_id=str(config_id), environment_id=str(environment_id), version_number=1, effective_at=now, status="ACTIVE", is_current=True))
    session.add(models.Portfolio(portfolio_id=str(portfolio_id), environment_id=str(environment_id), name="Test", status="ACTIVE"))
    session.add(models.StrategicEnvelope(strategic_envelope_id=str(envelope_id), configuration_version_id=str(config_id), portfolio_id=str(portfolio_id), effective_at=now, status="ACTIVE"))
    session.add(models.CapitalState(capital_state_id=str(capital_id), portfolio_id=str(portfolio_id), cash=10000, net_liquidation_value=10000, buying_power=10000, effective_at=now))
    session.add(models.PortfolioState(portfolio_state_id=str(state_id), portfolio_id=str(portfolio_id), configuration_version_id=str(config_id), capital_state_id=str(capital_id), effective_at=now, status="CURRENT"))
    session.add(models.PortfolioDecisionRecord(portfolio_decision_id=str(decision_id), portfolio_id=str(portfolio_id), source_portfolio_state_id=str(state_id), decision_type="BUY_OR_INCREASE", decision_horizon="TACTICAL", configuration_version_id=str(config_id), strategic_envelope_id=str(envelope_id), flow_id=str(flow_id), created_at=now, status="FINAL", rationale_summary="test"))
    session.flush()


def test_broker_order_fill_and_reconciliation_are_persisted():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        execution_id, decision_id, instrument_id, environment_id, flow_id = [uuid4() for _ in range(5)]
        seed(session, decision_id, instrument_id, environment_id, flow_id)
        action_id = uuid4()
        state = ExecutionRuntimeState(
            execution_id=execution_id,
            portfolio_decision_id=decision_id,
            financial_instrument_id=instrument_id,
            symbol="AAPL",
            side="BUY",
            target_quantity=5,
            remaining_quantity=0,
            client_order_id="cats-test",
            broker_order_id="B1",
            filled_quantity=5,
            average_fill_price=100,
            certainty_status="CONFIRMED",
            status="COMPLETED",
            last_execution_action_id=action_id,
        )
        store = SQLExecutionStateStore(session, environment_id=str(environment_id), flow_id=str(flow_id))
        store.save(state)

        order = BrokerOrder(
            broker_order_id="B1", client_order_id="cats-test", symbol="AAPL",
            side="BUY", quantity=5, order_type="MARKET", status="FILLED",
            filled_quantity=5, average_fill_price=100,
        )
        repo = BrokerFactRepository(session)
        rec_id = repo.persist_reconciled_order(
            state=state, order=order, certainty_status="CONFIRMED", resolved=True
        )

        assert session.query(models.ExecutionActionRecord).count() == 1
        assert session.query(models.OrderRecord).count() == 1
        assert session.query(models.BrokerActionResultRecord).count() == 1
        assert session.query(models.ReconciliationRecord).count() == 1
        assert session.query(models.FillRecord).count() == 1
        assert rec_id is not None
