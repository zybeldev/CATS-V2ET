from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.contracts import (
    Assessment,
    AlternativePosition,
    DecisionTarget,
    OptimizationRequest,
    PortfolioAlternative,
    PortfolioDecision,
    ValidationResult,
    ValidationRuleResult,
)
from cats.database.base import Base
from cats.database import models
from cats.repositories import MaterialContractRepository


def seed(session):
    now = datetime.now(timezone.utc)
    ids = {k: uuid4() for k in [
        "environment","instrument","flow","config","portfolio","capital","state","envelope","evidence"
    ]}
    session.add(models.Environment(environment_id=str(ids["environment"]), environment_code="PAPER", name="Paper", is_active=True))
    session.add(models.FinancialInstrument(financial_instrument_id=str(ids["instrument"]), instrument_type="EQUITY", symbol="AAPL", status="ACTIVE"))
    session.add(models.TraceFlow(flow_id=str(ids["flow"]), environment_id=str(ids["environment"]), flow_type="TEST", started_at=now, status="ACTIVE"))
    session.add(models.ConfigurationVersion(configuration_version_id=str(ids["config"]), environment_id=str(ids["environment"]), version_number=1, effective_at=now, status="ACTIVE", is_current=True))
    session.add(models.Portfolio(portfolio_id=str(ids["portfolio"]), environment_id=str(ids["environment"]), name="Test", status="ACTIVE"))
    session.add(models.StrategicEnvelope(strategic_envelope_id=str(ids["envelope"]), configuration_version_id=str(ids["config"]), portfolio_id=str(ids["portfolio"]), effective_at=now, status="ACTIVE"))
    session.add(models.CapitalState(capital_state_id=str(ids["capital"]), portfolio_id=str(ids["portfolio"]), cash=10000, net_liquidation_value=10000, buying_power=10000, effective_at=now))
    session.add(models.PortfolioState(portfolio_state_id=str(ids["state"]), portfolio_id=str(ids["portfolio"]), configuration_version_id=str(ids["config"]), capital_state_id=str(ids["capital"]), effective_at=now, status="CURRENT"))
    session.add(models.EvidenceItem(evidence_item_id=str(ids["evidence"]), evidence_type="PUBLIC_WEB", financial_instrument_id=str(ids["instrument"]), retrieved_at=now, environment_id=str(ids["environment"])))
    session.flush()
    return ids


def test_material_contracts_persist_across_taa_pms_pma_sys():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = seed(session)
        repo = MaterialContractRepository(session)

        assessment = Assessment(
            flow_id=ids["flow"], source="TAA", destination="PMA",
            configuration_version_id=ids["config"], assessment_id=uuid4(),
            financial_instrument_id=ids["instrument"], assessment_type="TACTICAL",
            horizon="TACTICAL", summary="positive opportunity", confidence=0.8,
            evidence_item_ids=[ids["evidence"]], status="FINAL",
        )
        repo.persist_assessment(assessment, portfolio_id=ids["portfolio"], source_portfolio_state_id=ids["state"])

        request = OptimizationRequest(
            flow_id=ids["flow"], source="PMA", destination="PMS",
            configuration_version_id=ids["config"], optimization_request_id=uuid4(),
            portfolio_id=ids["portfolio"], source_portfolio_state_id=ids["state"],
            strategic_envelope_id=ids["envelope"], assessment_ids=[assessment.assessment_id],
            requested_model="V2E_CONSTRAINED_EQUITY", status="REQUESTED",
        )
        repo.persist_optimization_request(request)

        alt = PortfolioAlternative(
            flow_id=ids["flow"], source="PMS", destination="PMA",
            configuration_version_id=ids["config"], portfolio_alternative_id=uuid4(),
            optimization_run_id=uuid4(), rank=1, feasibility_status="FEASIBLE",
            positions=[AlternativePosition(financial_instrument_id=ids["instrument"], target_weight=0.1, target_quantity=10)],
            status="FINAL",
        )
        repo.persist_portfolio_alternative(alt, optimization_request_id=request.optimization_request_id)

        decision = PortfolioDecision(
            flow_id=ids["flow"], source="PMA", destination="SYS",
            configuration_version_id=ids["config"], portfolio_decision_id=uuid4(),
            portfolio_id=ids["portfolio"], source_portfolio_state_id=ids["state"],
            decision_type="BUY_OR_INCREASE", horizon="TACTICAL",
            strategic_envelope_id=ids["envelope"], selected_portfolio_alternative_id=alt.portfolio_alternative_id,
            assessment_ids=[assessment.assessment_id],
            targets=[DecisionTarget(financial_instrument_id=ids["instrument"], target_weight=0.1, target_quantity=10)],
            rationale_summary="approved alternative", status="FINAL",
        )
        repo.persist_portfolio_decision(decision)

        validation = ValidationResult(
            flow_id=ids["flow"], source="SYS", destination="TEA",
            configuration_version_id=ids["config"], validation_result_id=uuid4(),
            portfolio_decision_id=decision.portfolio_decision_id, result="PASS",
            rule_results=[ValidationRuleResult(rule_code="PAPER", rule_version="1.0", result="PASS")],
            status="FINAL",
        )
        repo.persist_validation(validation, strategic_envelope_id=ids["envelope"])
        repo.commit()

        assert session.query(models.AssessmentRecord).count() == 1
        assert session.query(models.AssessmentEvidenceLinkRecord).count() == 1
        assert session.query(models.OptimizationRequestRecord).count() == 1
        assert session.query(models.PortfolioAlternativeRecord).count() == 1
        assert session.query(models.AlternativePositionRecord).count() == 1
        assert session.query(models.PortfolioDecisionRecord).count() == 1
        assert session.query(models.DecisionTargetRecord).count() == 1
        assert session.query(models.ValidationResultRecord).count() == 1
        assert session.query(models.ValidationRuleResultRecord).count() == 1
