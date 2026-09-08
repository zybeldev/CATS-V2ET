from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from cats.database import models
from cats.repositories import (
    AcceptedPortfolioStateRepository,
    BrokerFactRepository,
    MaterialContractRepository,
)
from cats.retrieval.models import EvidenceDocument, evidence_freshness_status
from cats.trace import PersistentTraceService, SQLTraceRepository


def utc_now():
    return datetime.now(timezone.utc)


class ProductionFlowPersistence:
    """SQL persistence boundary used directly by ProductionPaperFlow."""

    def __init__(self, session: Session):
        self.session = session
        self.material = MaterialContractRepository(session)
        self.broker_facts = BrokerFactRepository(session)
        self.portfolio_states = AcceptedPortfolioStateRepository(session)
        self.trace = PersistentTraceService(SQLTraceRepository(session))
        self.environment_id: UUID | None = None

    def _ensure_equity(self, *, instrument_id: UUID, symbol: str) -> None:
        if self.session.get(models.FinancialInstrument, str(instrument_id)) is None:
            self.session.add(models.FinancialInstrument(
                financial_instrument_id=str(instrument_id),
                instrument_type="EQUITY",
                symbol=symbol.upper(),
                status="ACTIVE",
            ))
            # Make the instrument visible to subsequent session.get() calls in
            # the same bootstrap. This matters when the requested symbol is
            # also present in the broker's current positions. Without the
            # flush, the same deterministic instrument ID can be queued twice.
            self.session.flush()

    def bootstrap(
        self,
        *,
        flow_id: UUID,
        instrument_id: UUID,
        symbol: str,
        config_id: UUID,
        strategic_envelope_id: UUID,
        portfolio_id: UUID,
        portfolio_state_id: UUID,
        cash: float,
        equity: float,
        buying_power: float,
        positions: list[dict] | None = None,
    ) -> UUID:
        now = utc_now()
        env = (
            self.session.query(models.Environment)
            .filter_by(environment_code="PAPER")
            .one_or_none()
        )
        if env is None:
            env = models.Environment(
                environment_id=str(uuid4()),
                environment_code="PAPER",
                name="CATS V2ET Paper",
                is_active=True,
            )
            self.session.add(env)
            self.session.flush()
        self.environment_id = UUID(env.environment_id)

        self._ensure_equity(instrument_id=instrument_id, symbol=symbol)
        for fact in positions or []:
            self._ensure_equity(
                instrument_id=fact["financial_instrument_id"],
                symbol=fact["symbol"],
            )

        if self.session.get(models.TraceFlow, str(flow_id)) is None:
            self.session.add(models.TraceFlow(
                flow_id=str(flow_id),
                environment_id=env.environment_id,
                flow_type="PRODUCTION_PAPER",
                started_at=now,
                status="ACTIVE",
            ))

        if self.session.get(models.ConfigurationVersion, str(config_id)) is None:
            current = (
                self.session.query(models.ConfigurationVersion)
                .filter_by(environment_id=env.environment_id, is_current=True)
                .first()
            )
            if current is not None:
                current.is_current = False
            next_version = (
                self.session.query(models.ConfigurationVersion)
                .filter_by(environment_id=env.environment_id)
                .count()
            ) + 1
            self.session.add(models.ConfigurationVersion(
                configuration_version_id=str(config_id),
                environment_id=env.environment_id,
                version_number=next_version,
                effective_at=now,
                status="ACTIVE",
                is_current=True,
                change_reason="CATS V2ET production PAPER flow bootstrap",
            ))

        self.session.flush()
        if self.session.get(models.Portfolio, str(portfolio_id)) is None:
            self.session.add(models.Portfolio(
                portfolio_id=str(portfolio_id),
                environment_id=env.environment_id,
                name="CATS V2ET Paper Portfolio",
                status="ACTIVE",
            ))

        self.session.flush()

        if self.session.get(models.StrategicEnvelope, str(strategic_envelope_id)) is None:
            self.session.add(models.StrategicEnvelope(
                strategic_envelope_id=str(strategic_envelope_id),
                configuration_version_id=str(config_id),
                portfolio_id=str(portfolio_id),
                effective_at=now,
                status="ACTIVE",
            ))

        if self.session.get(models.PortfolioState, str(portfolio_state_id)) is None:
            capital_id = uuid4()
            self.session.add(models.CapitalState(
                capital_state_id=str(capital_id),
                portfolio_id=str(portfolio_id),
                cash=cash,
                net_liquidation_value=equity,
                buying_power=buying_power,
                margin_used=0.0,
                leverage=0.0,
                currency="USD",
                effective_at=now,
            ))
            self.session.flush()
            self.session.add(models.PortfolioState(
                portfolio_state_id=str(portfolio_state_id),
                portfolio_id=str(portfolio_id),
                configuration_version_id=str(config_id),
                capital_state_id=str(capital_id),
                effective_at=now,
                status="CURRENT",
            ))
            self.session.flush()

            for fact in positions or []:
                quantity = float(fact["quantity"])
                if abs(quantity) < 1e-12:
                    continue
                self.session.add(models.Position(
                    portfolio_state_id=str(portfolio_state_id),
                    financial_instrument_id=str(fact["financial_instrument_id"]),
                    quantity=quantity,
                    average_cost=fact.get("average_cost"),
                    market_value=fact.get("market_value"),
                    currency=fact.get("currency", "USD"),
                    status="OPEN",
                ))

        self.session.commit()
        return self.environment_id

    def persist_evidence(self, documents: list[EvidenceDocument]) -> None:
        if self.environment_id is None:
            raise RuntimeError("bootstrap must run before evidence persistence")
        for document in documents:
            if self.session.get(models.EvidenceItem, str(document.evidence_document_id)) is None:
                self.session.add(models.EvidenceItem(
                    evidence_item_id=str(document.evidence_document_id),
                    evidence_type="PUBLIC_WEB",
                    financial_instrument_id=(
                        None if document.financial_instrument_id is None
                        else str(document.financial_instrument_id)
                    ),
                    external_reference=document.external_reference,
                    observed_at=document.observed_at,
                    retrieved_at=document.retrieved_at,
                    content_hash_reference=None,
                    freshness_status=evidence_freshness_status(document),
                    quality_status="UNREVIEWED",
                    environment_id=str(self.environment_id),
                ))
        self.session.commit()

    def complete_flow(self, flow_id: UUID, *, status: str) -> None:
        row = self.session.get(models.TraceFlow, str(flow_id))
        if row is not None:
            row.status = status
            row.completed_at = utc_now() if status == "COMPLETED" else None
            self.session.commit()
