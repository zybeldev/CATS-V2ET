from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.agents.tea import ExecutionRuntimeState
from cats.database.base import Base
from cats.database import models
from cats.runtime.sql_store import SQLExecutionStateStore


def seed_dependencies(session, environment_id, flow_id, instrument_id, portfolio_id, decision_id):
    from datetime import datetime, timezone
    config_id = str(uuid4())
    capital_id = str(uuid4())
    state_id = str(uuid4())
    envelope_id = str(uuid4())
    now = datetime.now(timezone.utc)

    session.add(models.Environment(
        environment_id=environment_id,
        environment_code="PAPER",
        name="Paper",
        is_active=True,
    ))
    session.add(models.FinancialInstrument(
        financial_instrument_id=str(instrument_id),
        instrument_type="EQUITY",
        symbol="AAPL",
        status="ACTIVE",
    ))
    session.add(models.TraceFlow(
        flow_id=flow_id,
        environment_id=environment_id,
        flow_type="TEST",
        started_at=now,
        status="ACTIVE",
    ))
    session.add(models.ConfigurationVersion(
        configuration_version_id=config_id,
        environment_id=environment_id,
        version_number=1,
        effective_at=now,
        status="ACTIVE",
        is_current=True,
    ))
    session.add(models.Portfolio(
        portfolio_id=str(portfolio_id),
        environment_id=environment_id,
        name="Test",
        status="ACTIVE",
    ))
    session.add(models.StrategicEnvelope(
        strategic_envelope_id=envelope_id,
        configuration_version_id=config_id,
        portfolio_id=str(portfolio_id),
        effective_at=now,
        status="ACTIVE",
    ))
    session.add(models.CapitalState(
        capital_state_id=capital_id,
        portfolio_id=str(portfolio_id),
        cash=10000,
        net_liquidation_value=10000,
        buying_power=10000,
        effective_at=now,
    ))
    session.add(models.PortfolioState(
        portfolio_state_id=state_id,
        portfolio_id=str(portfolio_id),
        configuration_version_id=config_id,
        capital_state_id=capital_id,
        effective_at=now,
        status="CURRENT",
    ))
    session.flush()
    session.add(models.PortfolioDecisionRecord(
        portfolio_decision_id=str(decision_id),
        portfolio_id=str(portfolio_id),
        source_portfolio_state_id=state_id,
        decision_type="BUY_OR_INCREASE",
        decision_horizon="TACTICAL",
        configuration_version_id=config_id,
        strategic_envelope_id=envelope_id,
        flow_id=flow_id,
        created_at=now,
        status="FINAL",
        rationale_summary="test",
    ))
    session.flush()


def test_sql_execution_store_preserves_recovery_identity():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    execution_id = uuid4()
    decision_id = uuid4()
    instrument_id = uuid4()
    portfolio_id = uuid4()
    environment_id = str(uuid4())
    flow_id = str(uuid4())

    with Session(engine) as session:
        seed_dependencies(session, environment_id, flow_id, instrument_id, portfolio_id, decision_id)
        store = SQLExecutionStateStore(session, environment_id=environment_id, flow_id=flow_id)
        original = ExecutionRuntimeState(
            execution_id=execution_id,
            portfolio_decision_id=decision_id,
            financial_instrument_id=instrument_id,
            symbol="AAPL",
            side="BUY",
            target_quantity=7.5,
            remaining_quantity=7.5,
            client_order_id="cats-123",
            broker_order_id="broker-456",
            certainty_status="UNKNOWN_OUTCOME",
            status="ACTIVE",
        )
        store.save(original)
        restored = store.load(execution_id)

        assert restored.symbol == "AAPL"
        assert restored.side == "BUY"
        assert restored.target_quantity == 7.5
        assert restored.client_order_id == "cats-123"
        assert restored.broker_order_id == "broker-456"
        assert restored.certainty_status == "UNKNOWN_OUTCOME"


def test_list_active_is_scoped_to_environment_and_flow():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    first_execution_id = uuid4()
    second_execution_id = uuid4()
    first_decision_id = uuid4()
    second_decision_id = uuid4()
    instrument_id = uuid4()
    portfolio_id = uuid4()
    environment_id = str(uuid4())
    first_flow_id = str(uuid4())
    second_flow_id = str(uuid4())

    with Session(engine) as session:
        seed_dependencies(
            session,
            environment_id,
            first_flow_id,
            instrument_id,
            portfolio_id,
            first_decision_id,
        )
        first_decision = session.get(
            models.PortfolioDecisionRecord, str(first_decision_id)
        )
        session.add(models.TraceFlow(
            flow_id=second_flow_id,
            environment_id=environment_id,
            flow_type="TEST",
            started_at=first_decision.created_at,
            status="ACTIVE",
        ))
        session.add(models.PortfolioDecisionRecord(
            portfolio_decision_id=str(second_decision_id),
            portfolio_id=first_decision.portfolio_id,
            source_portfolio_state_id=first_decision.source_portfolio_state_id,
            decision_type=first_decision.decision_type,
            decision_horizon=first_decision.decision_horizon,
            configuration_version_id=first_decision.configuration_version_id,
            strategic_envelope_id=first_decision.strategic_envelope_id,
            flow_id=second_flow_id,
            created_at=first_decision.created_at,
            status="FINAL",
            rationale_summary="second flow",
        ))
        session.flush()

        first_store = SQLExecutionStateStore(
            session, environment_id=environment_id, flow_id=first_flow_id
        )
        second_store = SQLExecutionStateStore(
            session, environment_id=environment_id, flow_id=second_flow_id
        )
        first_store.save(ExecutionRuntimeState(
            execution_id=first_execution_id,
            portfolio_decision_id=first_decision_id,
            financial_instrument_id=instrument_id,
            symbol="AAPL",
            side="BUY",
            target_quantity=1.0,
            remaining_quantity=1.0,
        ))
        second_store.save(ExecutionRuntimeState(
            execution_id=second_execution_id,
            portfolio_decision_id=second_decision_id,
            financial_instrument_id=instrument_id,
            symbol="AAPL",
            side="BUY",
            target_quantity=2.0,
            remaining_quantity=2.0,
        ))

        assert [state.execution_id for state in first_store.list_active()] == [
            first_execution_id
        ]
        assert [state.execution_id for state in second_store.list_active()] == [
            second_execution_id
        ]
