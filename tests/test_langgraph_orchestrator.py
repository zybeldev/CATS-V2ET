from __future__ import annotations

from uuid import uuid4

import pytest

pytest.importorskip("langgraph")

from cats.agents.pma import DeterministicPMAReasoningModel, PortfolioManagementAgent, PortfolioStateView
from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.contracts import Assessment
from cats.runtime.demo import DemoBroker, DemoOptimizer
from cats.runtime.langgraph_orchestrator import LangGraphV2ETOrchestrator
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext
from cats.systems.tes import TradingExecutionSystem


def _run(summary: str, *, outlook: str = "FAVORABLE", max_order_value: float = 25_000.0):
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
        summary=f"Outlook: {outlook}\n\n{summary}",
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
    pma = PortfolioManagementAgent(DeterministicPMAReasoningModel(), DemoOptimizer())
    tea = TradingExecutionAgent(
        DeterministicTEAReasoningModel(),
        TradingExecutionSystem(DemoBroker()),
    )
    orchestrator = LangGraphV2ETOrchestrator(
        pma=pma,
        sys_validator=SystemValidator(),
        tea=tea,
    )

    return orchestrator.run_from_assessment(
        assessment=assessment,
        portfolio_state=portfolio_state,
        strategic_envelope_id=uuid4(),
        configuration_version_id=config_id,
        governed_config=GovernedConfiguration(
            str(config_id),
            "PAPER",
            max_order_value=max_order_value,
        ),
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


def test_langgraph_backbone_completes_verified_execution_path():
    result = _run("positive attractive opportunity")

    assert result.completed is True
    assert result.terminal_state == "COMPLETED"
    assert result.terminal_reason == "EXECUTION_VERIFIED"
    assert result.path == ("TAA", "PMA", "SYS", "TEA", "COMPLETED")
    assert len(result.execution_ids) == 1


def test_langgraph_backbone_routes_sys_failure_without_invoking_tea():
    result = _run("positive attractive opportunity", max_order_value=100.0)

    assert result.completed is True
    assert result.terminal_state == "COMPLETED"
    assert result.terminal_reason == "SYS_REJECTED"
    assert result.path == ("TAA", "PMA", "SYS", "COMPLETED")
    assert result.execution_ids == ()


def test_langgraph_backbone_routes_no_change_without_invoking_tea():
    result = _run("mixed evidence with no portfolio implication", outlook="NEUTRAL")

    assert result.completed is True
    assert result.terminal_state == "COMPLETED"
    assert result.terminal_reason == "NO_CHANGE"
    assert result.path == ("TAA", "PMA", "SYS", "COMPLETED")
    assert result.execution_ids == ()
