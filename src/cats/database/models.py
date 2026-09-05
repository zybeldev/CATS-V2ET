from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def pk_uuid():
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))


class Environment(Base):
    __tablename__ = "SYS_Environment"

    environment_id: Mapped[str] = pk_uuid()
    environment_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FinancialInstrument(Base):
    __tablename__ = "FIN_Financial_Instrument"

    financial_instrument_id: Mapped[str] = pk_uuid()
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(256))
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    __table_args__ = (
        UniqueConstraint("instrument_type", "symbol", name="uq_fin_instrument_type_symbol"),
    )


class TraceFlow(Base):
    __tablename__ = "TRACE_Flow"

    flow_id: Mapped[str] = pk_uuid()
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )
    flow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    root_entity_type: Mapped[str | None] = mapped_column(String(64))
    root_entity_id: Mapped[str | None] = mapped_column(String(36))


class ConfigurationVersion(Base):
    __tablename__ = "SYS_Configuration_Version"

    configuration_version_id: Mapped[str] = pk_uuid()
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "environment_id", "version_number", name="uq_sys_configuration_version"
        ),
    )


class StrategicEnvelope(Base):
    __tablename__ = "SYS_Strategic_Envelope"

    strategic_envelope_id: Mapped[str] = pk_uuid()
    configuration_version_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id"),
        nullable=False,
    )
    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class Portfolio(Base):
    __tablename__ = "PMA_Portfolio"

    portfolio_id: Mapped[str] = pk_uuid()
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class CapitalState(Base):
    __tablename__ = "PMA_Capital_State"

    capital_state_id: Mapped[str] = pk_uuid()
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio.portfolio_id"), nullable=False
    )
    prior_capital_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("PMA_Capital_State.capital_state_id")
    )
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    net_liquidation_value: Mapped[float] = mapped_column(Float, nullable=False)
    buying_power: Mapped[float] = mapped_column(Float, nullable=False)
    margin_used: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    leverage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioState(Base):
    __tablename__ = "PMA_Portfolio_State"

    portfolio_state_id: Mapped[str] = pk_uuid()
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio.portfolio_id"), nullable=False
    )
    prior_portfolio_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("PMA_Portfolio_State.portfolio_state_id")
    )
    source_portfolio_decision_id: Mapped[str | None] = mapped_column(String(36))
    configuration_version_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id"),
        nullable=False,
    )
    capital_state_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Capital_State.capital_state_id"), nullable=False
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class Position(Base):
    __tablename__ = "PMA_Position"

    position_id: Mapped[str] = pk_uuid()
    portfolio_state_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_State.portfolio_state_id"), nullable=False
    )
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_cost: Mapped[float | None] = mapped_column(Float)
    market_value: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class EvidenceItem(Base):
    __tablename__ = "TAA_Evidence_Item"

    evidence_item_id: Mapped[str] = pk_uuid()
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    financial_instrument_id: Mapped[str | None] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id")
    )
    external_reference: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash_reference: Mapped[str | None] = mapped_column(String(128))
    freshness_status: Mapped[str | None] = mapped_column(String(32))
    quality_status: Mapped[str | None] = mapped_column(String(32))
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )


class AssessmentRecord(Base):
    __tablename__ = "TAA_Assessment"

    assessment_id: Mapped[str] = pk_uuid()
    assessment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment_horizon: Mapped[str] = mapped_column(String(32), nullable=False)
    financial_instrument_id: Mapped[str | None] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id")
    )
    portfolio_id: Mapped[str | None] = mapped_column(
        ForeignKey("PMA_Portfolio.portfolio_id")
    )
    source_portfolio_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("PMA_Portfolio_State.portfolio_state_id")
    )
    configuration_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id")
    )
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    assessment_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)


class OptimizationRequestRecord(Base):
    __tablename__ = "PMS_Optimization_Request"

    optimization_request_id: Mapped[str] = pk_uuid()
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio.portfolio_id"), nullable=False
    )
    source_portfolio_state_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_State.portfolio_state_id"), nullable=False
    )
    strategic_envelope_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Strategic_Envelope.strategic_envelope_id"), nullable=False
    )
    configuration_version_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id"),
        nullable=False,
    )
    requested_model: Mapped[str] = mapped_column(String(128), nullable=False)
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class PortfolioAlternativeRecord(Base):
    __tablename__ = "PMS_Portfolio_Alternative"

    portfolio_alternative_id: Mapped[str] = pk_uuid()
    optimization_request_id: Mapped[str] = mapped_column(
        ForeignKey("PMS_Optimization_Request.optimization_request_id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    feasibility_status: Mapped[str] = mapped_column(String(32), nullable=False)
    objective_value: Mapped[float | None] = mapped_column(Float)
    expected_return: Mapped[float | None] = mapped_column(Float)
    expected_risk: Mapped[float | None] = mapped_column(Float)
    expected_cost: Mapped[float | None] = mapped_column(Float)


class PortfolioDecisionRecord(Base):
    __tablename__ = "PMA_Portfolio_Decision"

    portfolio_decision_id: Mapped[str] = pk_uuid()
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio.portfolio_id"), nullable=False
    )
    source_portfolio_state_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_State.portfolio_state_id"), nullable=False
    )
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_horizon: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_version_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id"),
        nullable=False,
    )
    strategic_envelope_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Strategic_Envelope.strategic_envelope_id"), nullable=False
    )
    selected_portfolio_alternative_id: Mapped[str | None] = mapped_column(
        ForeignKey("PMS_Portfolio_Alternative.portfolio_alternative_id")
    )
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale_summary: Mapped[str] = mapped_column(Text, nullable=False)


class ValidationResultRecord(Base):
    __tablename__ = "SYS_Validation_Result"

    validation_result_id: Mapped[str] = pk_uuid()
    portfolio_decision_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_Decision.portfolio_decision_id"), nullable=False
    )
    configuration_version_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Configuration_Version.configuration_version_id"),
        nullable=False,
    )
    strategic_envelope_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Strategic_Envelope.strategic_envelope_id"), nullable=False
    )
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)


class ExecutionRecord(Base):
    __tablename__ = "TEA_Execution"

    execution_id: Mapped[str] = pk_uuid()
    portfolio_decision_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_Decision.portfolio_decision_id"), nullable=False
    )
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    execution_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    side: Mapped[str] = mapped_column(String(8), nullable=False, default="BUY")
    target_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    client_order_id: Mapped[str | None] = mapped_column(String(128))
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    certainty_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_SUBMITTED")
    last_execution_action_id: Mapped[str | None] = mapped_column(String(36))


class ExecutionStateRecord(Base):
    __tablename__ = "TEA_Execution_State"

    execution_state_id: Mapped[str] = pk_uuid()
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    prior_execution_state_id: Mapped[str | None] = mapped_column(
        ForeignKey("TEA_Execution_State.execution_state_id")
    )
    state_status: Mapped[str] = mapped_column(String(32), nullable=False)
    remaining_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    filled_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_fill_price: Mapped[float | None] = mapped_column(Float)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionActionRecord(Base):
    __tablename__ = "TEA_Execution_Action"

    execution_action_id: Mapped[str] = pk_uuid()
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    execution_state_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution_State.execution_state_id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_action_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    certainty_status: Mapped[str] = mapped_column(String(32), nullable=False)


class OrderRecord(Base):
    __tablename__ = "TES_Order"

    order_id: Mapped[str] = pk_uuid()
    execution_action_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution_Action.execution_action_id"), nullable=False
    )
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    client_order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class BrokerActionResultRecord(Base):
    __tablename__ = "TES_Broker_Action_Result"

    broker_action_result_id: Mapped[str] = pk_uuid()
    execution_action_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution_Action.execution_action_id"), nullable=False
    )
    order_id: Mapped[str | None] = mapped_column(ForeignKey("TES_Order.order_id"))
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    broker_status: Mapped[str | None] = mapped_column(String(64))
    certainty_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)


class TSSMeasurementSetRecord(Base):
    __tablename__ = "TSS_Measurement_Set"

    tss_measurement_set_id: Mapped[str] = pk_uuid()
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Environment.environment_id"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    flow_id: Mapped[str] = mapped_column(ForeignKey("TRACE_Flow.flow_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class TSSMeasurementRecord(Base):
    __tablename__ = "TSS_Measurement"

    tss_measurement_id: Mapped[str] = pk_uuid()
    tss_measurement_set_id: Mapped[str] = mapped_column(
        ForeignKey("TSS_Measurement_Set.tss_measurement_set_id"), nullable=False
    )
    measurement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(String(128))
    unit: Mapped[str | None] = mapped_column(String(32))

class TraceEventRecord(Base):
    __tablename__ = "TRACE_Event"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_component: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text)


class TraceProvenanceLinkRecord(Base):
    __tablename__ = "TRACE_Provenance_Link"

    provenance_link_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TraceLineageLinkRecord(Base):
    __tablename__ = "TRACE_Lineage_Link"

    lineage_link_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    child_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    child_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssessmentEvidenceLinkRecord(Base):
    __tablename__ = "TAA_Assessment_Evidence"

    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("TAA_Assessment.assessment_id"), primary_key=True
    )
    evidence_item_id: Mapped[str] = mapped_column(
        ForeignKey("TAA_Evidence_Item.evidence_item_id"), primary_key=True
    )


class AlternativePositionRecord(Base):
    __tablename__ = "PMS_Alternative_Position"

    alternative_position_id: Mapped[str] = pk_uuid()
    portfolio_alternative_id: Mapped[str] = mapped_column(
        ForeignKey("PMS_Portfolio_Alternative.portfolio_alternative_id"), nullable=False
    )
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    target_weight: Mapped[float] = mapped_column(Float, nullable=False)
    target_quantity: Mapped[float | None] = mapped_column(Float)


class DecisionTargetRecord(Base):
    __tablename__ = "PMA_Decision_Target"

    decision_target_id: Mapped[str] = pk_uuid()
    portfolio_decision_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_Decision.portfolio_decision_id"), nullable=False
    )
    financial_instrument_id: Mapped[str] = mapped_column(
        ForeignKey("FIN_Financial_Instrument.financial_instrument_id"), nullable=False
    )
    target_weight: Mapped[float | None] = mapped_column(Float)
    target_quantity: Mapped[float | None] = mapped_column(Float)


class ValidationRuleResultRecord(Base):
    __tablename__ = "SYS_Validation_Rule_Result"

    validation_rule_result_id: Mapped[str] = pk_uuid()
    validation_result_id: Mapped[str] = mapped_column(
        ForeignKey("SYS_Validation_Result.validation_result_id"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    configured_value: Mapped[str | None] = mapped_column(Text)
    observed_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)


class ExecutionResultRecord(Base):
    __tablename__ = "TEA_Execution_Result"

    execution_result_id: Mapped[str] = pk_uuid()
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    portfolio_decision_id: Mapped[str] = mapped_column(
        ForeignKey("PMA_Portfolio_Decision.portfolio_decision_id"), nullable=False
    )
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReconciliationRecord(Base):
    __tablename__ = "TEA_Reconciliation"

    reconciliation_id: Mapped[str] = pk_uuid()
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    client_order_id: Mapped[str | None] = mapped_column(String(128))
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    certainty_status: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    broker_status: Mapped[str | None] = mapped_column(String(64))
    filled_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_fill_price: Mapped[float | None] = mapped_column(Float)
    reconciled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FillRecord(Base):
    __tablename__ = "TES_Fill"

    fill_id: Mapped[str] = pk_uuid()
    order_id: Mapped[str] = mapped_column(
        ForeignKey("TES_Order.order_id"), nullable=False
    )
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("TEA_Execution.execution_id"), nullable=False
    )
    broker_fill_reference: Mapped[str | None] = mapped_column(String(128))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
