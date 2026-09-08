from __future__ import annotations

from uuid import uuid4

from cats.contracts import (
    Assessment,
    DecisionTarget,
    OptimizationRequest,
    PortfolioAlternative,
    PortfolioDecision,
)

from .models import PMADecisionContext, PortfolioStateView
from .reasoning import PMAReasoningModel


class PortfolioManagementAgent:
    """PMA owns Portfolio intent.

    PMS may construct alternatives, but PMA alone selects an alternative and
    issues the authoritative PortfolioDecision.
    """

    def __init__(self, reasoning_model: PMAReasoningModel, optimizer):
        self.reasoning_model = reasoning_model
        self.optimizer = optimizer

    def decide(
        self,
        *,
        assessment: Assessment,
        portfolio_state: PortfolioStateView,
        strategic_envelope_id,
        configuration_version_id,
        optimization_inputs: dict | None = None,
    ) -> PortfolioDecision:
        context = PMADecisionContext(
            portfolio_state=portfolio_state,
            strategic_envelope_id=strategic_envelope_id,
            configuration_version_id=configuration_version_id,
            assessment_id=assessment.assessment_id,
            financial_instrument_id=assessment.financial_instrument_id,
            assessment_summary=assessment.summary,
            assessment_confidence=assessment.confidence,
            assessment_horizon=assessment.horizon,
        )
        reasoning = self.reasoning_model.decide(context)

        if reasoning.action == "NO_CHANGE":
            return PortfolioDecision(
                flow_id=assessment.flow_id,
                source="PMA",
                destination="SYS",
                portfolio_decision_id=uuid4(),
                portfolio_id=portfolio_state.portfolio_id,
                source_portfolio_state_id=portfolio_state.portfolio_state_id,
                configuration_version_id=configuration_version_id,
                decision_type="NO_CHANGE",
                horizon=assessment.horizon,
                strategic_envelope_id=strategic_envelope_id,
                assessment_ids=[assessment.assessment_id],
                targets=[],
                rationale_summary=reasoning.rationale_summary,
                parent_ids=[assessment.assessment_id],
                status="FINAL",
            )

        if not reasoning.use_optimizer:
            raise ValueError("Portfolio-changing PMA decisions must use PMS in V2ET.")

        request = OptimizationRequest(
            flow_id=assessment.flow_id,
            source="PMA",
            destination="PMS",
            optimization_request_id=uuid4(),
            portfolio_id=portfolio_state.portfolio_id,
            source_portfolio_state_id=portfolio_state.portfolio_state_id,
            strategic_envelope_id=strategic_envelope_id,
            configuration_version_id=configuration_version_id,
            assessment_ids=[assessment.assessment_id],
            requested_model="V2E_CONSTRAINED_EQUITY",
            parent_ids=[assessment.assessment_id],
            status="REQUESTED",
        )

        alternative: PortfolioAlternative = self.optimizer.optimize(
            request=request,
            **(optimization_inputs or {}),
        )

        if alternative.feasibility_status != "FEASIBLE":
            return PortfolioDecision(
                flow_id=assessment.flow_id,
                source="PMA",
                destination="SYS",
                portfolio_decision_id=uuid4(),
                portfolio_id=portfolio_state.portfolio_id,
                source_portfolio_state_id=portfolio_state.portfolio_state_id,
                configuration_version_id=configuration_version_id,
                decision_type="NO_CHANGE",
                horizon=assessment.horizon,
                strategic_envelope_id=strategic_envelope_id,
                assessment_ids=[assessment.assessment_id],
                targets=[],
                rationale_summary="PMS returned no feasible PortfolioAlternative.",
                parent_ids=[assessment.assessment_id, alternative.portfolio_alternative_id],
                status="FINAL",
            )

        targets = [
            DecisionTarget(
                financial_instrument_id=p.financial_instrument_id,
                target_weight=p.target_weight,
                target_quantity=p.target_quantity,
            )
            for p in alternative.positions
        ]

        decision_type = self._classify_selected_target(
            alternative=alternative,
            portfolio_state=portfolio_state,
        )
        rationale_summary = reasoning.rationale_summary
        if decision_type != reasoning.action:
            rationale_summary = (
                f"{reasoning.rationale_summary} "
                f"The selected PMS target implies {decision_type} relative to the current Portfolio State; "
                "PMA classifies executable intent from the selected target rather than from assessment sentiment."
            )

        return PortfolioDecision(
            flow_id=assessment.flow_id,
            source="PMA",
            destination="SYS",
            portfolio_decision_id=uuid4(),
            portfolio_id=portfolio_state.portfolio_id,
            source_portfolio_state_id=portfolio_state.portfolio_state_id,
            configuration_version_id=configuration_version_id,
            decision_type=decision_type,
            horizon=assessment.horizon,
            strategic_envelope_id=strategic_envelope_id,
            selected_portfolio_alternative_id=alternative.portfolio_alternative_id,
            assessment_ids=[assessment.assessment_id],
            targets=targets,
            rationale_summary=rationale_summary,
            parent_ids=[assessment.assessment_id, alternative.portfolio_alternative_id],
            status="FINAL",
        )

    @staticmethod
    def _classify_selected_target(
        *,
        alternative: PortfolioAlternative,
        portfolio_state: PortfolioStateView,
        tolerance: float = 1e-12,
    ) -> str:
        """Classify PMA intent from the exact PMS target versus current Portfolio State.

        TAA/PMA reasoning determines whether optimization is warranted. Once PMA selects a
        feasible PMS alternative, the immutable PortfolioDecision must describe the actual
        target transition that TEA will execute.
        """
        current_by_instrument = {
            position.financial_instrument_id: float(position.quantity)
            for position in portfolio_state.positions
        }

        positive = False
        negative = False
        for position in alternative.positions:
            if position.target_quantity is None:
                continue
            current_quantity = current_by_instrument.get(position.financial_instrument_id, 0.0)
            delta = float(position.target_quantity) - current_quantity
            if delta > tolerance:
                positive = True
            elif delta < -tolerance:
                negative = True

        if positive and negative:
            return "REBALANCE"
        if positive:
            return "BUY_OR_INCREASE"
        if negative:
            return "SELL_OR_REDUCE"
        return "NO_CHANGE"
