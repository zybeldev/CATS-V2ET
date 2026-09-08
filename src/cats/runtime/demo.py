from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from cats.adapters.alpaca.models import BrokerActionOutcome, BrokerOrder
from cats.agents.pma import DeterministicPMAReasoningModel, PortfolioManagementAgent, PortfolioStateView
from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.contracts import Assessment, AlternativePosition, PortfolioAlternative
from cats.runtime.orchestrator import V2ETOrchestrator
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext
from cats.systems.tes import TradingExecutionSystem


class DemoOptimizer:
    def optimize(self, request, **kwargs):
        instrument_id = kwargs["instrument_id"]
        return PortfolioAlternative(
            flow_id=request.flow_id,
            source="PMS",
            destination="PMA",
            portfolio_alternative_id=uuid4(),
            optimization_run_id=uuid4(),
            configuration_version_id=request.configuration_version_id,
            rank=1,
            feasibility_status="FEASIBLE",
            positions=[AlternativePosition(financial_instrument_id=instrument_id, target_weight=0.10, target_quantity=5)],
            status="FINAL",
        )


class DemoBroker:
    def submit_market_order(self, *, symbol, quantity, side, client_order_id):
        order = BrokerOrder(
            broker_order_id="DEMO-BROKER-1",
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="MARKET",
            status="FILLED",
            filled_quantity=quantity,
            average_fill_price=100.0,
        )
        return BrokerActionOutcome("CONFIRMED", order=order)

    def get_order_by_client_order_id(self, client_order_id):
        return None


def run_demo():
    instrument_id = uuid4()
    config_id = uuid4()
    assessment = Assessment(
        flow_id=uuid4(), source="TAA", destination="PMA", assessment_id=uuid4(),
        financial_instrument_id=instrument_id, assessment_type="TACTICAL", horizon="TACTICAL",
        summary="Outlook: FAVORABLE\n\nPositive attractive opportunity", confidence=0.9, status="FINAL"
    )
    state = PortfolioStateView(
        portfolio_id=uuid4(), portfolio_state_id=uuid4(), cash_weight=0.5,
        total_equity_exposure=0.5, positions=()
    )
    pma = PortfolioManagementAgent(DeterministicPMAReasoningModel(), DemoOptimizer())
    tea = TradingExecutionAgent(DeterministicTEAReasoningModel(), TradingExecutionSystem(DemoBroker()))
    orchestrator = V2ETOrchestrator(pma=pma, sys_validator=SystemValidator(), tea=tea)
    result = orchestrator.run_from_assessment(
        assessment=assessment,
        portfolio_state=state,
        strategic_envelope_id=uuid4(),
        configuration_version_id=config_id,
        governed_config=GovernedConfiguration(str(config_id), "PAPER"),
        validation_context=ValidationContext(
            environment_code="PAPER", buying_power=100000, cash_weight=0.5,
            current_total_equity_exposure=0.5,
            instrument_types={instrument_id: "EQUITY"},
            estimated_order_values={instrument_id: 500},
            estimated_order_quantities={instrument_id: 5},
        ),
        symbol_by_instrument={instrument_id: "AAPL"},
        optimization_inputs={"instrument_id": instrument_id},
    )
    return result


if __name__ == "__main__":
    print(run_demo())
