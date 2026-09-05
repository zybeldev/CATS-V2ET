from uuid import uuid4

from cats.adapters.alpaca.models import BrokerOrder
from cats.agents.tea import ExecutionRuntimeState
from cats.runtime import InMemoryExecutionStateStore, RecoveryCoordinator
from cats.systems.tes import TradingExecutionSystem


class FakeBroker:
    def __init__(self, order):
        self.order = order

    def submit_market_order(self, **kwargs):
        raise AssertionError("Recovery must not submit a new order.")

    def get_order_by_client_order_id(self, client_order_id):
        return self.order


def test_recovery_reconciles_persisted_unknown_outcome():
    execution_id = uuid4()
    client_order_id = "cats-recovery-1"
    store = InMemoryExecutionStateStore()
    store.save(
        ExecutionRuntimeState(
            execution_id=execution_id,
            portfolio_decision_id=uuid4(),
            financial_instrument_id=uuid4(),
            symbol="AAPL",
            side="BUY",
            target_quantity=5,
            remaining_quantity=5,
            client_order_id=client_order_id,
            certainty_status="UNKNOWN_OUTCOME",
            status="ACTIVE",
        )
    )

    broker = FakeBroker(
        BrokerOrder(
            broker_order_id="B1",
            client_order_id=client_order_id,
            symbol="AAPL",
            side="BUY",
            quantity=5,
            order_type="MARKET",
            status="FILLED",
            filled_quantity=5,
            average_fill_price=100,
        )
    )
    coordinator = RecoveryCoordinator(store, TradingExecutionSystem(broker))
    results = coordinator.recover_active_executions()

    recovered = store.load(execution_id)
    assert results[0].recovered_certainty == "CONFIRMED"
    assert recovered.status == "COMPLETED"
    assert recovered.remaining_quantity == 0


def test_recovery_suspends_when_external_outcome_still_unknown():
    execution_id = uuid4()
    store = InMemoryExecutionStateStore()
    store.save(
        ExecutionRuntimeState(
            execution_id=execution_id,
            portfolio_decision_id=uuid4(),
            financial_instrument_id=uuid4(),
            symbol="AAPL",
            side="BUY",
            target_quantity=5,
            remaining_quantity=5,
            client_order_id="cats-missing",
            certainty_status="UNKNOWN_OUTCOME",
            status="ACTIVE",
        )
    )

    coordinator = RecoveryCoordinator(store, TradingExecutionSystem(FakeBroker(None)))
    coordinator.recover_active_executions()

    recovered = store.load(execution_id)
    assert recovered.status == "SUSPENDED"
    assert recovered.certainty_status == "UNKNOWN_OUTCOME"


def test_recovery_treats_broker_filled_status_as_terminal_despite_fractional_rounding():
    execution_id = uuid4()
    client_order_id = "cats-fractional-fill"
    target = 31.29106953
    store = InMemoryExecutionStateStore()
    store.save(
        ExecutionRuntimeState(
            execution_id=execution_id,
            portfolio_decision_id=uuid4(),
            financial_instrument_id=uuid4(),
            symbol="AAPL",
            side="BUY",
            target_quantity=target,
            remaining_quantity=target,
            client_order_id=client_order_id,
            certainty_status="CONFIRMED",
            status="ACTIVE",
        )
    )

    broker = FakeBroker(
        BrokerOrder(
            broker_order_id="B-FRACTIONAL",
            client_order_id=client_order_id,
            symbol="AAPL",
            side="BUY",
            quantity=target,
            order_type="MARKET",
            status="FILLED",
            filled_quantity=31.2910695,
            average_fill_price=100.0,
        )
    )

    RecoveryCoordinator(store, TradingExecutionSystem(broker)).recover_active_executions()

    recovered = store.load(execution_id)
    assert recovered.status == "COMPLETED"
    assert recovered.certainty_status == "CONFIRMED"
    assert recovered.remaining_quantity == 0.0
