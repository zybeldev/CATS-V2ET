from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.database.base import Base
from cats.database import models
from cats.repositories import AcceptedPortfolioStateRepository


def seed(session):
    now = datetime.now(timezone.utc)
    environment_id, instrument_id, config_id, portfolio_id, capital_id, state_id = [uuid4() for _ in range(6)]
    session.add(models.Environment(environment_id=str(environment_id), environment_code="PAPER", name="Paper", is_active=True))
    session.add(models.FinancialInstrument(financial_instrument_id=str(instrument_id), instrument_type="EQUITY", symbol="AAPL", status="ACTIVE"))
    session.add(models.ConfigurationVersion(configuration_version_id=str(config_id), environment_id=str(environment_id), version_number=1, effective_at=now, status="ACTIVE", is_current=True))
    session.add(models.Portfolio(portfolio_id=str(portfolio_id), environment_id=str(environment_id), name="Test", status="ACTIVE"))
    session.add(models.CapitalState(capital_state_id=str(capital_id), portfolio_id=str(portfolio_id), cash=10000, net_liquidation_value=10000, buying_power=10000, effective_at=now))
    session.add(models.PortfolioState(portfolio_state_id=str(state_id), portfolio_id=str(portfolio_id), configuration_version_id=str(config_id), capital_state_id=str(capital_id), effective_at=now, status="CURRENT"))
    session.flush()
    return portfolio_id, state_id, config_id, instrument_id


def test_broker_confirmed_state_becomes_new_accepted_pma_state():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        portfolio_id, prior_state_id, config_id, instrument_id = seed(session)
        repo = AcceptedPortfolioStateRepository(session)
        new_id = repo.persist_broker_confirmed_state(
            portfolio_id=portfolio_id,
            prior_portfolio_state_id=prior_state_id,
            source_portfolio_decision_id=uuid4(),
            configuration_version_id=config_id,
            cash=9000,
            equity=10000,
            buying_power=9000,
            positions=[{
                "financial_instrument_id": instrument_id,
                "quantity": 10,
                "average_cost": 100,
                "market_value": 1000,
            }],
        )
        row = session.get(models.PortfolioState, str(new_id))
        assert row.status == "ACCEPTED"
        assert row.prior_portfolio_state_id == str(prior_state_id)
        assert session.query(models.Position).filter_by(portfolio_state_id=str(new_id)).count() == 1


def test_invalid_broker_equity_is_rejected():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        portfolio_id, prior_state_id, config_id, instrument_id = seed(session)
        repo = AcceptedPortfolioStateRepository(session)
        with pytest.raises(ValueError):
            repo.persist_broker_confirmed_state(
                portfolio_id=portfolio_id,
                prior_portfolio_state_id=prior_state_id,
                source_portfolio_decision_id=uuid4(),
                configuration_version_id=config_id,
                cash=0,
                equity=0,
                buying_power=0,
                positions=[],
            )
