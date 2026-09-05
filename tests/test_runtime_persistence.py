from uuid import uuid4

from cats.agents.tea import ExecutionRuntimeState
from cats.runtime import InMemoryExecutionStateStore


def test_execution_state_round_trip_is_independent_copy():
    store = InMemoryExecutionStateStore()
    state = ExecutionRuntimeState(
        execution_id=uuid4(),
        portfolio_decision_id=uuid4(),
        financial_instrument_id=uuid4(),
        symbol="AAPL",
        side="BUY",
        target_quantity=5,
        remaining_quantity=5,
    )
    store.save(state)

    loaded = store.load(state.execution_id)
    loaded.remaining_quantity = 1

    reloaded = store.load(state.execution_id)
    assert reloaded.remaining_quantity == 5
