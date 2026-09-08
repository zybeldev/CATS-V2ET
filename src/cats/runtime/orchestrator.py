from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cats.agents.pma import PortfolioManagementAgent, PortfolioStateView
from cats.agents.tea import TradingExecutionAgent
from cats.contracts import Assessment
from cats.systems.sys import SystemValidator, ValidationContext, GovernedConfiguration


@dataclass
class VerticalSliceResult:
    assessment_id: UUID
    portfolio_decision_id: UUID
    validation_result_id: UUID
    execution_ids: list[UUID]
    completed: bool


class V2ETOrchestrator:
    """Minimal end-to-end coordinator. It routes contracts but owns no financial authority."""

    def __init__(self, *, pma: PortfolioManagementAgent, sys_validator: SystemValidator,
                 tea: TradingExecutionAgent, trace=None):
        self.pma = pma
        self.sys_validator = sys_validator
        self.tea = tea
        self.trace = trace

    def run_from_assessment(self, *, assessment: Assessment, portfolio_state: PortfolioStateView,
                            strategic_envelope_id, configuration_version_id,
                            governed_config: GovernedConfiguration,
                            validation_context: ValidationContext,
                            symbol_by_instrument: dict[UUID, str],
                            optimization_inputs: dict | None = None) -> VerticalSliceResult:
        decision = self.pma.decide(
            assessment=assessment,
            portfolio_state=portfolio_state,
            strategic_envelope_id=strategic_envelope_id,
            configuration_version_id=configuration_version_id,
            optimization_inputs=optimization_inputs,
        )

        validation = self.sys_validator.validate(decision, governed_config, validation_context)
        if validation.result != "PASS" or decision.decision_type == "NO_CHANGE":
            return VerticalSliceResult(
                assessment_id=assessment.assessment_id,
                portfolio_decision_id=decision.portfolio_decision_id,
                validation_result_id=validation.validation_result_id,
                execution_ids=[],
                completed=True,
            )

        states = self.tea.start_execution(
            decision=decision,
            validation=validation,
            symbol_by_instrument=symbol_by_instrument,
        )

        completed = True
        for state in states:
            self.tea.run_cycle(state=state)
            final = self.tea.run_cycle(state=state)
            completed = completed and bool(final and getattr(final, "verified", False))

        return VerticalSliceResult(
            assessment_id=assessment.assessment_id,
            portfolio_decision_id=decision.portfolio_decision_id,
            validation_result_id=validation.validation_result_id,
            execution_ids=[s.execution_id for s in states],
            completed=completed,
        )
