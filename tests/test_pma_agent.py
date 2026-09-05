from uuid import uuid4

from cats.agents.pma import (
    DeterministicPMAReasoningModel,
    PortfolioManagementAgent,
    PortfolioPositionView,
    PortfolioStateView,
)
from cats.contracts import Assessment, AlternativePosition, PortfolioAlternative


class FakeOptimizer:
    def __init__(self, feasible=True):
        self.feasible = feasible
        self.calls = 0

    def optimize(self, request, **kwargs):
        self.calls += 1
        instrument_id = request.assessment_ids[0]  # deterministic placeholder ID source
        return PortfolioAlternative(
            flow_id=request.flow_id,
            source="PMS",
            destination="PMA",
            portfolio_alternative_id=uuid4(),
            optimization_run_id=uuid4(),
            configuration_version_id=request.configuration_version_id,
            rank=1,
            feasibility_status="FEASIBLE" if self.feasible else "INFEASIBLE",
            positions=[] if not self.feasible else [
                AlternativePosition(
                    financial_instrument_id=instrument_id,
                    target_weight=0.10,
                    target_quantity=5,
                )
            ],
            status="FINAL",
            parent_ids=[request.optimization_request_id],
        )


def make_assessment(summary="attractive opportunity"):
    return Assessment(
        flow_id=uuid4(),
        source="TAA",
        destination="PMA",
        assessment_id=uuid4(),
        financial_instrument_id=uuid4(),
        assessment_type="TACTICAL",
        horizon="TACTICAL",
        summary=summary,
        confidence=0.8,
        status="FINAL",
    )


def make_state(*, positions=()):
    return PortfolioStateView(
        portfolio_id=uuid4(),
        portfolio_state_id=uuid4(),
        cash_weight=0.30,
        total_equity_exposure=0.70,
        positions=positions,
    )


def test_pma_uses_pms_for_portfolio_change():
    optimizer = FakeOptimizer(feasible=True)
    agent = PortfolioManagementAgent(
        DeterministicPMAReasoningModel(),
        optimizer,
    )

    assessment = make_assessment()
    decision = agent.decide(
        assessment=assessment,
        portfolio_state=make_state(),
        strategic_envelope_id=uuid4(),
        configuration_version_id=uuid4(),
    )

    assert optimizer.calls == 1
    assert decision.decision_type == "BUY_OR_INCREASE"
    assert decision.selected_portfolio_alternative_id is not None
    assert decision.source == "PMA"
    assert decision.destination == "SYS"


def test_pma_does_not_call_pms_for_no_change():
    optimizer = FakeOptimizer(feasible=True)
    agent = PortfolioManagementAgent(
        DeterministicPMAReasoningModel(),
        optimizer,
    )

    decision = agent.decide(
        assessment=make_assessment("neutral conditions"),
        portfolio_state=make_state(),
        strategic_envelope_id=uuid4(),
        configuration_version_id=uuid4(),
    )

    assert optimizer.calls == 0
    assert decision.decision_type == "NO_CHANGE"
    assert decision.targets == []


def test_infeasible_pms_result_does_not_become_modified_portfolio():
    optimizer = FakeOptimizer(feasible=False)
    agent = PortfolioManagementAgent(
        DeterministicPMAReasoningModel(),
        optimizer,
    )

    decision = agent.decide(
        assessment=make_assessment(),
        portfolio_state=make_state(),
        strategic_envelope_id=uuid4(),
        configuration_version_id=uuid4(),
    )

    assert optimizer.calls == 1
    assert decision.decision_type == "NO_CHANGE"
    assert decision.selected_portfolio_alternative_id is None
    assert decision.targets == []


class TargetedOptimizer:
    def __init__(self, instrument_id, target_quantity):
        self.instrument_id = instrument_id
        self.target_quantity = target_quantity

    def optimize(self, request, **kwargs):
        return PortfolioAlternative(
            flow_id=request.flow_id,
            source="PMS",
            destination="PMA",
            portfolio_alternative_id=uuid4(),
            optimization_run_id=uuid4(),
            configuration_version_id=request.configuration_version_id,
            rank=1,
            feasibility_status="FEASIBLE",
            positions=[
                AlternativePosition(
                    financial_instrument_id=self.instrument_id,
                    target_weight=0.10,
                    target_quantity=self.target_quantity,
                )
            ],
            status="FINAL",
            parent_ids=[request.optimization_request_id],
        )


def test_pma_classifies_selected_target_from_actual_quantity_delta():
    assessment = make_assessment("positive opportunity")
    instrument_id = assessment.financial_instrument_id
    state = make_state(positions=(
        PortfolioPositionView(
            financial_instrument_id=instrument_id,
            symbol="AAPL",
            quantity=30.786674449,
            market_value=10_050.0,
            portfolio_weight=0.1005,
        ),
    ))
    agent = PortfolioManagementAgent(
        DeterministicPMAReasoningModel(),
        TargetedOptimizer(instrument_id, 30.726077695195773),
    )

    decision = agent.decide(
        assessment=assessment,
        portfolio_state=state,
        strategic_envelope_id=uuid4(),
        configuration_version_id=uuid4(),
    )

    assert decision.decision_type == "SELL_OR_REDUCE"
    assert "selected PMS target implies SELL_OR_REDUCE" in decision.rationale_summary
