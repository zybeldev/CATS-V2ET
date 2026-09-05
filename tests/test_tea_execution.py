from uuid import uuid4

from cats.adapters.alpaca.models import BrokerActionOutcome, BrokerOrder
from cats.agents.tea import DeterministicTEAReasoningModel, ExecutionContext, TradingExecutionAgent
from cats.contracts import DecisionTarget, PortfolioDecision, ValidationResult
from cats.systems.tes import TradingExecutionSystem


class FakeBroker:
    def __init__(self, outcome="FILLED"):
        self.outcome = outcome
        self.submissions = 0
        self.order = None

    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        self.submissions += 1
        if self.outcome == "TIMEOUT":
            return BrokerActionOutcome("UNKNOWN_OUTCOME", error_code="TIMEOUT")
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
        return BrokerActionOutcome("CONFIRMED", order=self.order)

    def get_order_by_client_order_id(self, client_order_id):
        return self.order


def make_decision_and_validation():
    instrument_id = uuid4()
    decision = PortfolioDecision(
        flow_id=uuid4(),
        source="PMA",
        destination="SYS",
        portfolio_decision_id=uuid4(),
        portfolio_id=uuid4(),
        source_portfolio_state_id=uuid4(),
        configuration_version_id=uuid4(),
        decision_type="BUY_OR_INCREASE",
        horizon="TACTICAL",
        strategic_envelope_id=uuid4(),
        targets=[DecisionTarget(financial_instrument_id=instrument_id, target_quantity=5)],
        rationale_summary="test",
        status="FINAL",
    )
    validation = ValidationResult(
        flow_id=decision.flow_id,
        source="SYS",
        destination="TEA",
        validation_result_id=uuid4(),
        portfolio_decision_id=decision.portfolio_decision_id,
        configuration_version_id=decision.configuration_version_id,
        result="PASS",
        status="FINAL",
    )
    return decision, validation, instrument_id


def test_tea_executes_only_sys_passed_decision():
    broker = FakeBroker()
    agent = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(broker),
    )
    decision, validation, instrument_id = make_decision_and_validation()
    state = agent.start_execution(
        decision=decision,
        validation=validation,
        symbol_by_instrument={instrument_id: "AAPL"},
    )[0]
    result = agent.run_cycle(state=state, last_price=100)
    assert result.certainty_status == "CONFIRMED"
    assert broker.submissions == 1
    final = agent.run_cycle(state=state, last_price=100)
    assert final.result_status == "COMPLETED"
    assert final.verified is True


def test_unknown_outcome_is_not_blindly_resubmitted():
    broker = FakeBroker(outcome="TIMEOUT")
    agent = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(broker),
    )
    decision, validation, instrument_id = make_decision_and_validation()
    state = agent.start_execution(
        decision=decision,
        validation=validation,
        symbol_by_instrument={instrument_id: "AAPL"},
    )[0]

    first = agent.run_cycle(state=state)
    assert first.certainty_status == "UNKNOWN_OUTCOME"
    assert broker.submissions == 1

    second = agent.run_cycle(state=state)
    assert broker.submissions == 1
    assert second is None

def test_active_broker_order_is_reconciled():
    model = DeterministicTEAReasoningModel()
    context = ExecutionContext(
        execution_id=uuid4(),
        portfolio_decision_id=uuid4(),
        financial_instrument_id=uuid4(),
        symbol="AAPL",
        side="BUY",
        target_quantity=5.0,
        remaining_quantity=5.0,
        last_price=100.0,
        broker_order_id="B1",
        client_order_id="cats-test",
        certainty_status="CONFIRMED",
    )

    result = model.decide(context)

    assert result.action == "RECONCILE"


def test_tea_reconcile_treats_broker_filled_status_as_terminal_despite_fractional_rounding():
    class RoundedFilledBroker(FakeBroker):
        def __init__(self):
            super().__init__()
            self.order = BrokerOrder(
                broker_order_id="B-FRACTIONAL",
                client_order_id="cats-fractional-tea",
                symbol="AAPL",
                side="BUY",
                quantity=31.29106953,
                order_type="MARKET",
                status="FILLED",
                filled_quantity=31.2910695,
                average_fill_price=100.0,
            )

    broker = RoundedFilledBroker()
    agent = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(broker),
    )
    state = __import__("cats.agents.tea", fromlist=["ExecutionRuntimeState"]).ExecutionRuntimeState(
        execution_id=uuid4(),
        portfolio_decision_id=uuid4(),
        financial_instrument_id=uuid4(),
        symbol="AAPL",
        side="BUY",
        target_quantity=31.29106953,
        remaining_quantity=31.29106953,
        client_order_id="cats-fractional-tea",
        broker_order_id="B-FRACTIONAL",
        certainty_status="CONFIRMED",
        status="ACTIVE",
    )

    result = agent.run_cycle(state=state)

    assert result.result_status == "COMPLETED"
    assert result.verified is True
    assert state.status == "COMPLETED"
    assert state.remaining_quantity == 0.0


def test_tea_skips_order_when_current_weight_is_within_standard_execution_tolerance():
    broker = FakeBroker()
    agent = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(broker),
    )
    decision, validation, instrument_id = make_decision_and_validation()
    decision.targets[0] = DecisionTarget(
        financial_instrument_id=instrument_id,
        target_weight=0.10,
        target_quantity=30.726077695195773,
    )

    states = agent.start_execution(
        decision=decision,
        validation=validation,
        symbol_by_instrument={instrument_id: "AAPL"},
        current_quantity_by_instrument={instrument_id: 30.786674449},
        current_weight_by_instrument={instrument_id: 0.1002},
    )

    assert states == []
    assert broker.submissions == 0


def test_tea_creates_execution_when_current_weight_is_outside_standard_tolerance():
    broker = FakeBroker()
    agent = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(broker),
    )
    decision, validation, instrument_id = make_decision_and_validation()
    decision.targets[0] = DecisionTarget(
        financial_instrument_id=instrument_id,
        target_weight=0.10,
        target_quantity=30.0,
    )

    states = agent.start_execution(
        decision=decision,
        validation=validation,
        symbol_by_instrument={instrument_id: "AAPL"},
        current_quantity_by_instrument={instrument_id: 30.786674449},
        current_weight_by_instrument={instrument_id: 0.1010},
    )

    assert len(states) == 1
    assert states[0].side == "SELL"
    assert abs(states[0].target_quantity - 0.786674449) < 1e-12
