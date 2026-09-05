from uuid import uuid4

from cats.adapters.alpaca.models import BrokerActionOutcome, BrokerOrder
from cats.agents.tea import (
    DeterministicTEAReasoningModel,
    ExecutionRuntimeState,
    PersistentTradingExecutionAgent,
    TradingExecutionAgent,
)
from cats.runtime import InMemoryExecutionStateStore
from cats.systems.tes import TradingExecutionSystem


class FillBroker:
    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        return BrokerActionOutcome(
            "CONFIRMED",
            BrokerOrder(
                broker_order_id="B1",
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="MARKET",
                status="FILLED",
                filled_quantity=quantity,
                average_fill_price=100,
            ),
        )

    def get_order_by_client_order_id(self, client_order_id):
        return None


def test_persistent_tea_saves_execution_transition():
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

    tea = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(FillBroker()),
    )
    persistent = PersistentTradingExecutionAgent(tea, store)
    persistent.run_cycle(execution_id=state.execution_id)

    saved = store.load(state.execution_id)
    assert saved.remaining_quantity == 0
    assert saved.filled_quantity == 5
    assert saved.broker_order_id == "B1"
