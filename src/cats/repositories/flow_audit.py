from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.orm import Session

from cats.database import models


@dataclass(frozen=True)
class FlowAuditSummary:
    flow_id: str
    complete: bool
    missing_stages: tuple[str, ...]
    evidence_count: int
    assessment_count: int
    optimization_request_count: int
    alternative_count: int
    decision_count: int
    validation_count: int
    execution_count: int
    order_count: int
    fill_count: int
    reconciliation_count: int
    execution_result_count: int
    accepted_portfolio_state_count: int
    provenance_count: int
    lineage_count: int


class FlowAuditRepository:
    """Reconstructs the material CATS chain from durable SQL records."""

    REQUIRED_STAGES = (
        "evidence",
        "assessment",
        "optimization_request",
        "alternative",
        "decision",
        "validation",
        "execution",
        "order",
        "reconciliation",
        "execution_result",
        "accepted_portfolio_state",
        "provenance",
        "lineage",
    )

    def __init__(self, session: Session):
        self.session = session

    def summarize(self, flow_id: str) -> FlowAuditSummary:
        assessments = (
            self.session.query(models.AssessmentRecord)
            .filter_by(flow_id=flow_id)
            .all()
        )
        assessment_ids = [a.assessment_id for a in assessments]

        evidence_count = 0
        if assessment_ids:
            evidence_count = (
                self.session.query(models.AssessmentEvidenceLinkRecord)
                .filter(models.AssessmentEvidenceLinkRecord.assessment_id.in_(assessment_ids))
                .count()
            )

        optimization_requests = (
            self.session.query(models.OptimizationRequestRecord)
            .filter_by(flow_id=flow_id)
            .all()
        )
        request_ids = [r.optimization_request_id for r in optimization_requests]

        alternatives = []
        if request_ids:
            alternatives = (
                self.session.query(models.PortfolioAlternativeRecord)
                .filter(models.PortfolioAlternativeRecord.optimization_request_id.in_(request_ids))
                .all()
            )

        decisions = (
            self.session.query(models.PortfolioDecisionRecord)
            .filter_by(flow_id=flow_id)
            .all()
        )
        decision_ids = [d.portfolio_decision_id for d in decisions]

        validations = (
            self.session.query(models.ValidationResultRecord)
            .filter_by(flow_id=flow_id)
            .all()
        )

        executions = (
            self.session.query(models.ExecutionRecord)
            .filter_by(flow_id=flow_id)
            .all()
        )
        execution_ids = [e.execution_id for e in executions]

        orders = []
        reconciliations = []
        execution_results = []
        fills = []
        if execution_ids:
            orders = (
                self.session.query(models.OrderRecord)
                .filter(models.OrderRecord.execution_id.in_(execution_ids))
                .all()
            )
            order_ids = [o.order_id for o in orders]
            if order_ids:
                fills = (
                    self.session.query(models.FillRecord)
                    .filter(models.FillRecord.order_id.in_(order_ids))
                    .all()
                )
            reconciliations = (
                self.session.query(models.ReconciliationRecord)
                .filter(models.ReconciliationRecord.execution_id.in_(execution_ids))
                .all()
            )
            execution_results = (
                self.session.query(models.ExecutionResultRecord)
                .filter(models.ExecutionResultRecord.execution_id.in_(execution_ids))
                .all()
            )

        accepted_states = []
        if decision_ids:
            accepted_states = (
                self.session.query(models.PortfolioState)
                .filter(
                    models.PortfolioState.source_portfolio_decision_id.in_(decision_ids),
                    models.PortfolioState.status == "ACCEPTED",
                )
                .all()
            )

        provenance_count = (
            self.session.query(models.TraceProvenanceLinkRecord)
            .join(
                models.AssessmentRecord,
                models.TraceProvenanceLinkRecord.target_entity_id
                == models.AssessmentRecord.assessment_id,
            )
            .filter(models.AssessmentRecord.flow_id == flow_id)
            .count()
        )
        lineage_count = (
            self.session.query(models.TraceLineageLinkRecord)
            .filter_by(flow_id=flow_id)
            .count()
        )

        counts = {
            "evidence": evidence_count,
            "assessment": len(assessments),
            "optimization_request": len(optimization_requests),
            "alternative": len(alternatives),
            "decision": len(decisions),
            "validation": len(validations),
            "execution": len(executions),
            "order": len(orders),
            "reconciliation": len(reconciliations),
            "execution_result": len(execution_results),
            "accepted_portfolio_state": len(accepted_states),
            "provenance": provenance_count,
            "lineage": lineage_count,
        }

        missing = tuple(stage for stage in self.REQUIRED_STAGES if counts[stage] == 0)

        return FlowAuditSummary(
            flow_id=flow_id,
            complete=not missing,
            missing_stages=missing,
            evidence_count=evidence_count,
            assessment_count=len(assessments),
            optimization_request_count=len(optimization_requests),
            alternative_count=len(alternatives),
            decision_count=len(decisions),
            validation_count=len(validations),
            execution_count=len(executions),
            order_count=len(orders),
            fill_count=len(fills),
            reconciliation_count=len(reconciliations),
            execution_result_count=len(execution_results),
            accepted_portfolio_state_count=len(accepted_states),
            provenance_count=provenance_count,
            lineage_count=lineage_count,
        )
