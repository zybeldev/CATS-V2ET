from __future__ import annotations

from uuid import uuid4

from cats.agents.pma import DeterministicPMAReasoningModel, PortfolioManagementAgent, PortfolioStateView
from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.contracts import Assessment
from cats.runtime.demo import DemoBroker, DemoOptimizer
from cats.runtime.langgraph_orchestrator import LangGraphV2ETOrchestrator
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext
from cats.systems.tes import TradingExecutionSystem


def main() -> int:
    instrument_id = uuid4()
    config_id = uuid4()
    assessment = Assessment(
        flow_id=uuid4(),
        source="TAA",
        destination="PMA",
        assessment_id=uuid4(),
        financial_instrument_id=instrument_id,
        assessment_type="TACTICAL",
        horizon="TACTICAL",
        summary="positive attractive opportunity",
        confidence=0.9,
        status="FINAL",
    )
    portfolio_state = PortfolioStateView(
        portfolio_id=uuid4(),
        portfolio_state_id=uuid4(),
        cash_weight=0.5,
        total_equity_exposure=0.5,
        positions=(),
    )

    orchestrator = LangGraphV2ETOrchestrator(
        pma=PortfolioManagementAgent(DeterministicPMAReasoningModel(), DemoOptimizer()),
        sys_validator=SystemValidator(),
        tea=TradingExecutionAgent(
            DeterministicTEAReasoningModel(),
            TradingExecutionSystem(DemoBroker()),
        ),
    )

    result = orchestrator.run_from_assessment(
        assessment=assessment,
        portfolio_state=portfolio_state,
        strategic_envelope_id=uuid4(),
        configuration_version_id=config_id,
        governed_config=GovernedConfiguration(str(config_id), "PAPER"),
        validation_context=ValidationContext(
            environment_code="PAPER",
            buying_power=100_000,
            cash_weight=0.5,
            current_total_equity_exposure=0.5,
            instrument_types={instrument_id: "EQUITY"},
            estimated_order_values={instrument_id: 500},
            estimated_order_quantities={instrument_id: 5},
        ),
        symbol_by_instrument={instrument_id: "AAPL"},
        optimization_inputs={"instrument_id": instrument_id},
    )

    print("LangGraph CATS backbone: PASS")
    print(f"path={' -> '.join(result.path)}")
    print(f"terminal_state={result.terminal_state}")
    print(f"terminal_reason={result.terminal_reason}")
    print(f"executions={len(result.execution_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
