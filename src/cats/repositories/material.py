from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from cats.contracts import (
    Assessment,
    ExecutionResult,
    OptimizationRequest,
    PortfolioAlternative,
    PortfolioDecision,
    ValidationResult,
)
from cats.database import models


def utc_now():
    return datetime.now(timezone.utc)


class MaterialContractRepository:
    """Persists material CATS contracts and their deterministic sub-records."""

    def __init__(self, session: Session):
        self.session = session

    def persist_assessment(
        self,
        assessment: Assessment,
        *,
        portfolio_id: UUID | None = None,
        source_portfolio_state_id: UUID | None = None,
    ) -> None:
        self.session.add(
            models.AssessmentRecord(
                assessment_id=str(assessment.assessment_id),
                assessment_type=assessment.assessment_type,
                assessment_horizon=assessment.horizon,
                financial_instrument_id=str(assessment.financial_instrument_id),
                portfolio_id=None if portfolio_id is None else str(portfolio_id),
                source_portfolio_state_id=(
                    None if source_portfolio_state_id is None else str(source_portfolio_state_id)
                ),
                configuration_version_id=(
                    None if assessment.configuration_version_id is None
                    else str(assessment.configuration_version_id)
                ),
                flow_id=str(assessment.flow_id),
                created_at=assessment.created_at,
                status=assessment.status,
                assessment_summary=assessment.summary,
                confidence=assessment.confidence,
            )
        )
        self.session.flush()
        for evidence_id in assessment.evidence_item_ids:
            self.session.add(
                models.AssessmentEvidenceLinkRecord(
                    assessment_id=str(assessment.assessment_id),
                    evidence_item_id=str(evidence_id),
                )
            )

    def persist_optimization_request(self, request: OptimizationRequest) -> None:
        self.session.add(
            models.OptimizationRequestRecord(
                optimization_request_id=str(request.optimization_request_id),
                portfolio_id=str(request.portfolio_id),
                source_portfolio_state_id=str(request.source_portfolio_state_id),
                strategic_envelope_id=str(request.strategic_envelope_id),
                configuration_version_id=str(request.configuration_version_id),
                requested_model=request.requested_model,
                flow_id=str(request.flow_id),
                status=request.status,
            )
        )

    def persist_portfolio_alternative(
        self,
        alternative: PortfolioAlternative,
        *,
        optimization_request_id: UUID,
    ) -> None:
        self.session.add(
            models.PortfolioAlternativeRecord(
                portfolio_alternative_id=str(alternative.portfolio_alternative_id),
                optimization_request_id=str(optimization_request_id),
                rank=alternative.rank,
                feasibility_status=alternative.feasibility_status,
                objective_value=alternative.objective_value,
                expected_return=alternative.expected_return,
                expected_risk=alternative.expected_risk,
                expected_cost=alternative.expected_cost,
            )
        )
        self.session.flush()
        for position in alternative.positions:
            self.session.add(
                models.AlternativePositionRecord(
                    portfolio_alternative_id=str(alternative.portfolio_alternative_id),
                    financial_instrument_id=str(position.financial_instrument_id),
                    target_weight=position.target_weight,
                    target_quantity=position.target_quantity,
                )
            )

    def persist_portfolio_decision(self, decision: PortfolioDecision) -> None:
        self.session.add(
            models.PortfolioDecisionRecord(
                portfolio_decision_id=str(decision.portfolio_decision_id),
                portfolio_id=str(decision.portfolio_id),
                source_portfolio_state_id=str(decision.source_portfolio_state_id),
                decision_type=decision.decision_type,
                decision_horizon=decision.horizon,
                configuration_version_id=str(decision.configuration_version_id),
                strategic_envelope_id=str(decision.strategic_envelope_id),
                selected_portfolio_alternative_id=(
                    None if decision.selected_portfolio_alternative_id is None
                    else str(decision.selected_portfolio_alternative_id)
                ),
                flow_id=str(decision.flow_id),
                created_at=decision.created_at,
                status=decision.status,
                rationale_summary=decision.rationale_summary,
            )
        )
        self.session.flush()
        for target in decision.targets:
            self.session.add(
                models.DecisionTargetRecord(
                    portfolio_decision_id=str(decision.portfolio_decision_id),
                    financial_instrument_id=str(target.financial_instrument_id),
                    target_weight=target.target_weight,
                    target_quantity=target.target_quantity,
                )
            )

    def persist_validation(
        self,
        validation: ValidationResult,
        *,
        strategic_envelope_id: UUID,
    ) -> None:
        self.session.add(
            models.ValidationResultRecord(
                validation_result_id=str(validation.validation_result_id),
                portfolio_decision_id=str(validation.portfolio_decision_id),
                configuration_version_id=str(validation.configuration_version_id),
                strategic_envelope_id=str(strategic_envelope_id),
                flow_id=str(validation.flow_id),
                validated_at=validation.created_at,
                result=validation.result,
            )
        )
        self.session.flush()
        for rule in validation.rule_results:
            self.session.add(
                models.ValidationRuleResultRecord(
                    validation_result_id=str(validation.validation_result_id),
                    rule_code=rule.rule_code,
                    rule_version=rule.rule_version,
                    result=rule.result,
                    configured_value=rule.configured_value,
                    observed_value=rule.observed_value,
                    reason=rule.reason,
                )
            )

    def persist_execution_result(self, result: ExecutionResult) -> None:
        self.session.add(
            models.ExecutionResultRecord(
                execution_result_id=str(result.execution_result_id),
                execution_id=str(result.execution_id),
                portfolio_decision_id=str(result.portfolio_decision_id),
                flow_id=str(result.flow_id),
                result_status=result.result_status,
                verified=result.verified,
                created_at=result.created_at,
            )
        )

    def commit(self) -> None:
        self.session.commit()
