from uuid import uuid4

import pytest

from cats.agents.pma import PortfolioStateView
from cats.agents.pma.state_update import PortfolioStateUpdater, VerifiedExecutionFact
from cats.contracts import ExecutionResult


def make_execution(verified):
    return ExecutionResult(
        flow_id=uuid4(),
        source="TEA",
        destination="PMA",
        execution_result_id=uuid4(),
        execution_id=uuid4(),
        portfolio_decision_id=uuid4(),
        result_status="COMPLETED",
        verified=verified,
        status="FINAL",
    )


def test_unverified_execution_cannot_change_portfolio_state():
    updater = PortfolioStateUpdater()
    state = PortfolioStateView(
        portfolio_id=uuid4(),
        portfolio_state_id=uuid4(),
        cash_weight=1.0,
        total_equity_exposure=0.0,
        positions=(),
    )
    fact = VerifiedExecutionFact(uuid4(), "AAPL", 5, 100)

    with pytest.raises(ValueError):
        updater.apply_verified_execution(
            prior_state=state,
            execution_result=make_execution(False),
            fact=fact,
            portfolio_value=10_000,
        )


def test_verified_execution_creates_new_portfolio_state():
    updater = PortfolioStateUpdater()
    instrument_id = uuid4()
    state = PortfolioStateView(
        portfolio_id=uuid4(),
        portfolio_state_id=uuid4(),
        cash_weight=1.0,
        total_equity_exposure=0.0,
        positions=(),
    )
    new_state = updater.apply_verified_execution(
        prior_state=state,
        execution_result=make_execution(True),
        fact=VerifiedExecutionFact(instrument_id, "AAPL", 5, 100),
        portfolio_value=10_000,
    )
    assert new_state.portfolio_state_id != state.portfolio_state_id
    assert new_state.positions[0].quantity == 5
    assert new_state.total_equity_exposure == 0.05
