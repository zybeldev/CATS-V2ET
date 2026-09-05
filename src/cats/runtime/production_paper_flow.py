from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from cats.adapters.alpaca import AlpacaPaperAdapter
from cats.adapters.evidence.public import PublicEvidenceRequest, PublicWebEvidenceSource
from cats.adapters.embeddings import LocalFastEmbedEmbeddingAdapter
from cats.adapters.llm import OpenAIReasoningAdapter
from cats.adapters.market_data import AlpacaMarketDataAdapter
from cats.agents.pma import (
    DeterministicPMAReasoningModel,
    PortfolioManagementAgent,
    PortfolioPositionView,
    PortfolioStateView,
)
from cats.agents.tea import DeterministicTEAReasoningModel, TradingExecutionAgent
from cats.agents.taa import TradingAssessmentAgent
from cats.retrieval import InMemoryVectorStore, RetrievalService
from cats.retrieval.models import evidence_age_seconds, evidence_freshness_status
from cats.runtime.flow_visibility import FlowVisibilityBuilder, FlowVisibilityReport
from cats.runtime.persistent_paper_flow import PersistentExecutionCoordinator
from cats.runtime.production_persistence import ProductionFlowPersistence
from cats.runtime.sql_store import SQLExecutionStateStore
from cats.services.pms import EquityCandidate, EquityOptimizationConstraints, PMAOptimizerAdapter
from cats.services.tss import TradingSignalService
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext
from cats.systems.tes import TradingExecutionSystem


@dataclass(frozen=True)
class ProductionPaperFlowInput:
    symbol: str
    evidence_urls: tuple[str, ...]
    openai_model: str | None = None
    max_target_weight: float = 0.10


@dataclass(frozen=True)
class ProductionPaperFlowResult:
    symbol: str
    flow_id: UUID
    assessment_id: UUID
    portfolio_decision_id: UUID
    validation_result_id: UUID
    execution_ids: tuple[UUID, ...]
    completed: bool
    accepted_portfolio_state_id: UUID | None = None
    visibility_report: FlowVisibilityReport | None = field(default=None, repr=False)


def instrument_id_for_symbol(symbol: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"cats:v2e:equity:{symbol.upper()}")


def _round_or_none(value, digits=6):
    return None if value is None else round(float(value), digits)


class ProductionPaperFlow:
    """Real PAPER vertical slice with optional SQL durability.

    Runtime coordinates the authority chain; it does not originate investment intent.
    The visibility report is a read-only projection for operators/UI consumers and
    never participates in authority, optimization, validation, or execution.
    """

    def __init__(
        self,
        *,
        alpaca_api_key: str,
        alpaca_api_secret: str,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        session=None,
        broker=None,
        market_data=None,
        reasoning=None,
        embeddings=None,
        evidence_source=None,
    ):
        self.broker = broker or AlpacaPaperAdapter(alpaca_api_key, alpaca_api_secret)
        self.market_data = market_data or AlpacaMarketDataAdapter(alpaca_api_key, alpaca_api_secret)
        if reasoning is None:
            if not openai_api_key or not openai_model:
                raise ValueError(
                    "OpenAI API key and model are required only when no reasoning adapter is injected."
                )
            reasoning = OpenAIReasoningAdapter(
                api_key=openai_api_key,
                model=openai_model,
            )
        self.reasoning = reasoning
        self.embeddings = embeddings or LocalFastEmbedEmbeddingAdapter()
        self.evidence_source = evidence_source or PublicWebEvidenceSource()
        self.persistence = None if session is None else ProductionFlowPersistence(session)
        self.session = session
        self.last_visibility_report: FlowVisibilityReport | None = None

    def run(self, request: ProductionPaperFlowInput) -> ProductionPaperFlowResult:
        symbol = request.symbol.upper()
        instrument_id = instrument_id_for_symbol(symbol)
        flow_id = uuid4()
        visibility = FlowVisibilityBuilder(flow_id=flow_id, symbol=symbol)

        def publish(outcome: str) -> FlowVisibilityReport:
            report = visibility.build(outcome=outcome)
            self.last_visibility_report = report
            return report

        publish("STARTED")

        config_id = uuid4()
        strategic_envelope_id = uuid4()
        portfolio_id = uuid5(NAMESPACE_URL, "cats:v2e:paper:portfolio:default")
        initial_state_id = uuid4()

        account = self.broker.get_account()
        broker_positions = {p.symbol.upper(): p for p in self.broker.get_positions()}
        portfolio_value = float(account.equity)
        if portfolio_value <= 0:
            raise RuntimeError("Broker account equity must be positive.")

        current_position = broker_positions.get(symbol)
        current_quantity = 0.0 if current_position is None else current_position.quantity
        current_market_value = (
            0.0 if current_position is None or current_position.market_value is None
            else current_position.market_value
        )

        positions = ()
        if current_position is not None and abs(current_quantity) > 0:
            positions = (
                PortfolioPositionView(
                    financial_instrument_id=instrument_id,
                    symbol=symbol,
                    quantity=current_quantity,
                    market_value=current_market_value,
                    portfolio_weight=current_market_value / portfolio_value,
                ),
            )

        state = PortfolioStateView(
            portfolio_id=portfolio_id,
            portfolio_state_id=initial_state_id,
            cash_weight=max(0.0, float(account.cash) / portfolio_value),
            total_equity_exposure=sum(
                abs(float(p.market_value or 0.0)) for p in broker_positions.values()
            ) / portfolio_value,
            positions=positions,
        )

        initial_position_facts = []
        for broker_position in broker_positions.values():
            iid = instrument_id_for_symbol(broker_position.symbol)
            initial_position_facts.append({
                "financial_instrument_id": iid,
                "symbol": broker_position.symbol.upper(),
                "quantity": broker_position.quantity,
                "average_cost": broker_position.average_entry_price,
                "market_value": broker_position.market_value,
                "currency": "USD",
            })

        visibility.stage(
            "STARTING PORTFOLIO STATE",
            account_equity=_round_or_none(account.equity),
            cash=_round_or_none(account.cash),
            buying_power=_round_or_none(account.buying_power),
            current_symbol_quantity=_round_or_none(current_quantity),
            current_symbol_market_value=_round_or_none(current_market_value),
            current_symbol_weight=_round_or_none(
                0.0 if portfolio_value == 0 else current_market_value / portfolio_value
            ),
        )
        publish("ACTIVE")

        if self.persistence is not None:
            environment_id = self.persistence.bootstrap(
                flow_id=flow_id,
                instrument_id=instrument_id,
                symbol=symbol,
                config_id=config_id,
                strategic_envelope_id=strategic_envelope_id,
                portfolio_id=portfolio_id,
                portfolio_state_id=initial_state_id,
                cash=float(account.cash),
                equity=float(account.equity),
                buying_power=float(account.buying_power),
                positions=initial_position_facts,
            )
            self.persistence.trace.record_event(
                flow_id=flow_id,
                event_type="FLOW_STARTED",
                source_component="RUNTIME",
                entity_type="TRACE_Flow",
                entity_id=flow_id,
                status="ACTIVE",
                payload={"symbol": symbol},
            )

        bars = self.market_data.get_daily_bars(symbol, lookback_days=90)
        measurements = TradingSignalService().calculate_equity_measurements(bars)
        measurement_time = datetime.now(timezone.utc)
        visibility.stage(
            "MARKET STATE — TSS",
            calculated_at=measurement_time,
            last_price=_round_or_none(measurements.last_price),
            return_1_period=_round_or_none(measurements.return_1_period),
            sma_short=_round_or_none(measurements.sma_short),
            sma_long=_round_or_none(measurements.sma_long),
            momentum=_round_or_none(measurements.momentum),
            annualized_volatility=_round_or_none(measurements.annualized_volatility),
            average_volume=_round_or_none(measurements.average_volume),
        )
        publish("ACTIVE")

        retrieval = RetrievalService(self.embeddings, InMemoryVectorStore())
        documents = [
            self.evidence_source.ingest(
                PublicEvidenceRequest(
                    url=url,
                    source_name=url,
                    financial_instrument_id=instrument_id,
                )
            )
            for url in request.evidence_urls
        ]
        if not documents:
            raise ValueError("At least one public evidence URL is required.")
        retrieval.index(documents)

        ingest_time = datetime.now(timezone.utc)
        visibility.stage(
            "INPUT / EVIDENCE",
            status="INGESTED",
            items=[
                {
                    "source": document.source_name,
                    "url": document.external_reference,
                    "source_date": document.observed_at,
                    "source_age_days": (
                        None
                        if evidence_age_seconds(document, as_of=ingest_time) is None
                        else round(evidence_age_seconds(document, as_of=ingest_time) / 86400.0, 3)
                    ),
                    "freshness_status": evidence_freshness_status(document, as_of=ingest_time),
                    "retrieved_at": document.retrieved_at,
                    "source_date_origin": document.metadata.get("source_date_origin"),
                    "text_excerpt": document.text[:280],
                }
                for document in documents
            ],
        )
        publish("ACTIVE")

        if self.persistence is not None:
            self.persistence.persist_evidence(documents)

        taa = TradingAssessmentAgent(retrieval=retrieval, reasoning_model=self.reasoning)
        assessment = taa.assess_equity(
            flow_id=flow_id,
            financial_instrument_id=instrument_id,
            symbol=symbol,
            horizon="TACTICAL",
            assessment_type="TACTICAL",
            query_text=f"Current material financial evidence for {symbol}",
            tss_measurements=measurements,
            configuration_version_id=config_id,
        )

        evidence_time = datetime.now(timezone.utc)
        visibility.stage(
            "INPUT / EVIDENCE",
            status="RETRIEVED",
            items=[
                {
                    "rank": item.rank,
                    "relevance_score": _round_or_none(item.score),
                    "source": item.document.source_name,
                    "url": item.document.external_reference,
                    "source_date": item.document.observed_at,
                    "source_age_days": (
                        None
                        if evidence_age_seconds(item.document, as_of=evidence_time) is None
                        else round(
                            evidence_age_seconds(item.document, as_of=evidence_time) / 86400.0,
                            3,
                        )
                    ),
                    "freshness_status": evidence_freshness_status(
                        item.document, as_of=evidence_time
                    ),
                    "retrieved_at": item.document.retrieved_at,
                    "text_excerpt": item.document.text[:280],
                }
                for item in taa.last_retrieved_evidence
            ],
        )
        visibility.stage(
            "TAA ASSESSMENT",
            horizon=assessment.horizon,
            assessment_type=assessment.assessment_type,
            summary=assessment.summary,
            confidence=assessment.confidence,
            valid_until=assessment.valid_until,
            evidence_items_used=len(assessment.evidence_item_ids),
            source_date_check=[
                evidence_freshness_status(item.document, as_of=evidence_time)
                for item in taa.last_retrieved_evidence
            ],
        )
        publish("ACTIVE")

        if self.persistence is not None:
            self.persistence.material.persist_assessment(
                assessment,
                portfolio_id=portfolio_id,
                source_portfolio_state_id=initial_state_id,
            )
            self.persistence.material.commit()
            for evidence_id in assessment.evidence_item_ids:
                self.persistence.trace.add_provenance(
                    target_entity_type="TAA_Assessment",
                    target_entity_id=assessment.assessment_id,
                    source_entity_type="TAA_Evidence_Item",
                    source_entity_id=evidence_id,
                    relationship_type="SUPPORTED_BY",
                )

        config = GovernedConfiguration(
            configuration_version_id=str(config_id),
            environment_code="PAPER",
            max_position_weight=min(0.25, request.max_target_weight),
            max_total_equity_exposure=0.95,
            min_cash_reserve_weight=0.05,
        )

        pms = PMAOptimizerAdapter()
        pma = PortfolioManagementAgent(DeterministicPMAReasoningModel(), pms)
        score = max(0.0, float(assessment.confidence or 0.0))
        candidate = EquityCandidate(
            financial_instrument_id=instrument_id,
            score=score,
            expected_risk=measurements.annualized_volatility,
        )
        constraints = EquityOptimizationConstraints(
            max_position_weight=config.max_position_weight,
            max_total_equity_exposure=config.max_total_equity_exposure,
            min_cash_reserve_weight=config.min_cash_reserve_weight,
        )

        decision = pma.decide(
            assessment=assessment,
            portfolio_state=state,
            strategic_envelope_id=strategic_envelope_id,
            configuration_version_id=config_id,
            optimization_inputs={
                "candidates": [candidate],
                "constraints": constraints,
                "portfolio_value": portfolio_value,
                "prices_by_instrument": {instrument_id: measurements.last_price},
            },
        )

        alternative = pms.last_alternative
        visibility.stage(
            "PMS PORTFOLIO ALTERNATIVE",
            status=("NOT_USED" if alternative is None else alternative.feasibility_status),
            rank=None if alternative is None else alternative.rank,
            objective_value=None if alternative is None else _round_or_none(alternative.objective_value),
            expected_return=None if alternative is None else _round_or_none(alternative.expected_return),
            expected_risk=None if alternative is None else _round_or_none(alternative.expected_risk),
            positions=[] if alternative is None else [
                {
                    "financial_instrument_id": position.financial_instrument_id,
                    "target_weight": _round_or_none(position.target_weight),
                    "target_quantity": _round_or_none(position.target_quantity),
                }
                for position in alternative.positions
            ],
            diagnostics=[] if alternative is None else alternative.diagnostics,
        )
        visibility.stage(
            "PMA DECISION",
            decision_type=decision.decision_type,
            horizon=decision.horizon,
            rationale=decision.rationale_summary,
            selected_portfolio_alternative_id=decision.selected_portfolio_alternative_id,
            targets=[
                {
                    "financial_instrument_id": target.financial_instrument_id,
                    "target_weight": _round_or_none(target.target_weight),
                    "target_quantity": _round_or_none(target.target_quantity),
                }
                for target in decision.targets
            ],
        )
        publish("ACTIVE")

        if self.persistence is not None:
            if pms.last_request is not None:
                self.persistence.material.persist_optimization_request(pms.last_request)
            if pms.last_alternative is not None and pms.last_request is not None:
                self.persistence.material.persist_portfolio_alternative(
                    pms.last_alternative,
                    optimization_request_id=pms.last_request.optimization_request_id,
                )
            self.persistence.material.persist_portfolio_decision(decision)
            self.persistence.material.commit()

            self.persistence.trace.add_lineage(
                flow_id=flow_id,
                parent_entity_type="TAA_Assessment",
                parent_entity_id=assessment.assessment_id,
                child_entity_type="PMA_Portfolio_Decision",
                child_entity_id=decision.portfolio_decision_id,
                relationship_type="INFORMED",
                sequence_number=1,
            )
            if pms.last_alternative is not None:
                self.persistence.trace.add_lineage(
                    flow_id=flow_id,
                    parent_entity_type="PMS_Portfolio_Alternative",
                    parent_entity_id=pms.last_alternative.portfolio_alternative_id,
                    child_entity_type="PMA_Portfolio_Decision",
                    child_entity_id=decision.portfolio_decision_id,
                    relationship_type="SELECTED_BY",
                    sequence_number=2,
                )

        target = next(
            (t for t in decision.targets if t.financial_instrument_id == instrument_id),
            None,
        )
        target_quantity = (
            current_quantity
            if target is None or target.target_quantity is None
            else float(target.target_quantity)
        )
        quantity_delta = target_quantity - current_quantity
        estimated_order_value = abs(quantity_delta) * measurements.last_price
        current_weight = current_market_value / portfolio_value
        target_weight = (
            current_weight
            if target is None or target.target_weight is None
            else float(target.target_weight)
        )
        weight_delta = target_weight - current_weight
        execution_weight_tolerance = TradingExecutionAgent.DEFAULT_EXECUTION_WEIGHT_TOLERANCE
        target_within_execution_tolerance = (
            target is not None
            and target.target_weight is not None
            and abs(weight_delta) <= execution_weight_tolerance
        )
        projected_equity_exposure = max(0.0, target_weight)
        projected_cash_weight = max(0.0, 1.0 - projected_equity_exposure)

        semantic_consistency = "CONSISTENT"
        if decision.decision_type == "BUY_OR_INCREASE" and quantity_delta < -1e-12:
            semantic_consistency = "WARNING_BUY_INTENT_REQUIRES_SELL_DELTA"
        elif decision.decision_type == "SELL_OR_REDUCE" and quantity_delta > 1e-12:
            semantic_consistency = "WARNING_SELL_INTENT_REQUIRES_BUY_DELTA"

        visibility.stage(
            "PMA DECISION",
            decision_type=decision.decision_type,
            horizon=decision.horizon,
            rationale=decision.rationale_summary,
            semantic_consistency=semantic_consistency,
            current_quantity=_round_or_none(current_quantity),
            proposed_quantity=_round_or_none(target_quantity),
            required_quantity_delta=_round_or_none(quantity_delta),
            delta_side=(
                "NONE" if abs(quantity_delta) < 1e-12 else ("BUY" if quantity_delta > 0 else "SELL")
            ),
            current_weight=_round_or_none(current_weight),
            target_weight=_round_or_none(target_weight),
            required_weight_delta=_round_or_none(weight_delta),
            execution_weight_tolerance=execution_weight_tolerance,
            target_within_execution_tolerance=target_within_execution_tolerance,
            estimated_order_value=_round_or_none(estimated_order_value),
        )

        validation_context = ValidationContext(
            environment_code="PAPER",
            buying_power=float(account.buying_power),
            cash_weight=projected_cash_weight,
            current_total_equity_exposure=projected_equity_exposure,
            instrument_types={instrument_id: "EQUITY"},
            estimated_order_values={instrument_id: estimated_order_value},
            estimated_order_quantities={instrument_id: quantity_delta},
        )
        validation = SystemValidator().validate(decision, config, validation_context)

        visibility.stage(
            "SYS VALIDATION",
            status=validation.result,
            result=validation.result,
            rules=[
                {
                    "rule": rule.rule_code,
                    "result": rule.result,
                    "configured": rule.configured_value,
                    "observed": rule.observed_value,
                    "reason": rule.reason,
                }
                for rule in validation.rule_results
            ],
        )
        publish("ACTIVE")

        if self.persistence is not None:
            self.persistence.material.persist_validation(
                validation,
                strategic_envelope_id=strategic_envelope_id,
            )
            self.persistence.material.commit()
            self.persistence.trace.add_lineage(
                flow_id=flow_id,
                parent_entity_type="PMA_Portfolio_Decision",
                parent_entity_id=decision.portfolio_decision_id,
                child_entity_type="SYS_Validation_Result",
                child_entity_id=validation.validation_result_id,
                relationship_type="VALIDATED_AS",
                sequence_number=3,
            )

        if validation.result != "PASS" or decision.decision_type == "NO_CHANGE":
            reason = (
                "SYS rejected the PortfolioDecision."
                if validation.result != "PASS"
                else "PMA issued NO_CHANGE; execution is not required."
            )
            visibility.stage("TEA EXECUTION", status="NOT_STARTED", reason=reason)
            visibility.stage("BROKER RESULT", status="NOT_APPLICABLE", reason=reason)
            visibility.stage("RECONCILIATION", status="NOT_APPLICABLE", reason=reason)
            visibility.stage(
                "ACCEPTED PORTFOLIO STATE",
                status="UNCHANGED",
                reason="No new broker-confirmed state was required by this flow.",
            )
            if self.persistence is not None:
                self.persistence.complete_flow(flow_id, status="COMPLETED")
            report = publish("COMPLETED_NO_EXECUTION")
            return ProductionPaperFlowResult(
                symbol=symbol,
                flow_id=flow_id,
                assessment_id=assessment.assessment_id,
                portfolio_decision_id=decision.portfolio_decision_id,
                validation_result_id=validation.validation_result_id,
                execution_ids=(),
                completed=True,
                accepted_portfolio_state_id=None,
                visibility_report=report,
            )

        tes = TradingExecutionSystem(self.broker)
        tea = TradingExecutionAgent(DeterministicTEAReasoningModel(), tes)
        states = tea.start_execution(
            decision=decision,
            validation=validation,
            symbol_by_instrument={instrument_id: symbol},
            current_quantity_by_instrument={instrument_id: current_quantity},
            current_weight_by_instrument={instrument_id: current_weight},
        )

        if not states:
            reason = (
                "Broker-confirmed current position already satisfies the PMA-authorized target "
                f"within TEA execution tolerance (+/- {tea.execution_weight_tolerance:.4%})."
            )
            visibility.stage(
                "TEA EXECUTION",
                status="TARGET_ALREADY_SATISFIED",
                reason=reason,
                current_weight=_round_or_none(current_weight),
                target_weight=_round_or_none(target_weight),
                weight_delta=_round_or_none(weight_delta),
                execution_weight_tolerance=tea.execution_weight_tolerance,
            )
            visibility.stage("BROKER RESULT", status="NO_ORDER_REQUIRED", reason=reason)
            visibility.stage(
                "RECONCILIATION",
                status="TARGET_WITHIN_TOLERANCE",
                reason=reason,
            )
            visibility.stage(
                "ACCEPTED PORTFOLIO STATE",
                status="UNCHANGED",
                reason=(
                    "The existing broker-confirmed Portfolio State remains authoritative; "
                    "the tolerated residual becomes part of the actual state used by future PMS rebalancing."
                ),
            )
            if self.persistence is not None:
                self.persistence.complete_flow(flow_id, status="COMPLETED")
            report = publish("COMPLETED_TARGET_ALREADY_SATISFIED")
            return ProductionPaperFlowResult(
                symbol=symbol,
                flow_id=flow_id,
                assessment_id=assessment.assessment_id,
                portfolio_decision_id=decision.portfolio_decision_id,
                validation_result_id=validation.validation_result_id,
                execution_ids=(),
                completed=True,
                accepted_portfolio_state_id=None,
                visibility_report=report,
            )

        visibility.stage(
            "TEA EXECUTION",
            status="AUTHORIZED",
            executions=[
                {
                    "execution_id": state_item.execution_id,
                    "symbol": state_item.symbol,
                    "intended_side": state_item.side,
                    "authorized_delta_quantity": _round_or_none(state_item.target_quantity),
                    "current_portfolio_quantity": _round_or_none(current_quantity),
                    "target_portfolio_quantity": _round_or_none(target_quantity),
                }
                for state_item in states
            ],
        )
        publish("ACTIVE")

        if self.persistence is None:
            completed = True
            final_results = []
            for execution_state in states:
                first = tea.run_cycle(state=execution_state, last_price=measurements.last_price)
                final = tea.run_cycle(state=execution_state, last_price=measurements.last_price)
                final_results.append(final or first)
                completed = completed and bool(final and getattr(final, "verified", False))

            visibility.stage(
                "BROKER RESULT",
                status=("NOT_APPLICABLE" if not states else ("COMPLETED" if completed else "INCOMPLETE")),
                orders=[
                    {
                        "execution_id": state_item.execution_id,
                        "side": state_item.side,
                        "client_order_id": state_item.client_order_id,
                        "broker_order_id": state_item.broker_order_id,
                        "certainty_status": state_item.certainty_status,
                        "filled_quantity": _round_or_none(state_item.filled_quantity),
                        "average_fill_price": _round_or_none(state_item.average_fill_price),
                        "status": state_item.status,
                    }
                    for state_item in states
                ],
            )
            visibility.stage(
                "RECONCILIATION",
                status=("VERIFIED" if completed else "UNVERIFIED"),
                executions=[
                    {
                        "execution_id": state_item.execution_id,
                        "remaining_quantity": _round_or_none(state_item.remaining_quantity),
                        "certainty_status": state_item.certainty_status,
                        "verified": bool(
                            final_results[index]
                            and getattr(final_results[index], "verified", False)
                        ),
                    }
                    for index, state_item in enumerate(states)
                ],
            )
            visibility.stage(
                "ACCEPTED PORTFOLIO STATE",
                status="NOT_PERSISTED",
                reason="Flow was run without the SQL persistence boundary.",
            )
            report = publish("COMPLETED" if completed else "SUSPENDED")
            return ProductionPaperFlowResult(
                symbol=symbol,
                flow_id=flow_id,
                assessment_id=assessment.assessment_id,
                portfolio_decision_id=decision.portfolio_decision_id,
                validation_result_id=validation.validation_result_id,
                execution_ids=tuple(s.execution_id for s in states),
                completed=completed,
                visibility_report=report,
            )

        store = SQLExecutionStateStore(
            self.session,
            environment_id=str(self.persistence.environment_id),
            flow_id=str(flow_id),
        )
        execution = PersistentExecutionCoordinator(
            tea=tea,
            store=store,
            trace=self.persistence.trace,
            tes=tes,
            broker_fact_repository=self.persistence.broker_facts,
            material_repository=self.persistence.material,
        )
        outcomes = execution.execute_states(
            flow_id=flow_id,
            states=states,
            last_price=measurements.last_price,
        )
        completed = all(o.completed and o.verified for o in outcomes)
        persisted_states = [store.load(state_item.execution_id) or state_item for state_item in states]

        visibility.stage(
            "BROKER RESULT",
            status=("NOT_APPLICABLE" if not persisted_states else ("COMPLETED" if completed else "INCOMPLETE")),
            orders=[
                {
                    "execution_id": state_item.execution_id,
                    "side": state_item.side,
                    "client_order_id": state_item.client_order_id,
                    "broker_order_id": state_item.broker_order_id,
                    "certainty_status": state_item.certainty_status,
                    "filled_quantity": _round_or_none(state_item.filled_quantity),
                    "average_fill_price": _round_or_none(state_item.average_fill_price),
                    "status": state_item.status,
                }
                for state_item in persisted_states
            ],
        )
        visibility.stage(
            "RECONCILIATION",
            status=("VERIFIED" if completed else "REQUIRES_RECOVERY"),
            executions=[
                {
                    "execution_id": outcome.execution_id,
                    "completed": outcome.completed,
                    "verified": outcome.verified,
                    "result_status": (
                        None
                        if outcome.execution_result is None
                        else outcome.execution_result.result_status
                    ),
                    "reconciliation_id": (
                        None
                        if outcome.execution_result is None
                        else outcome.execution_result.reconciliation_id
                    ),
                }
                for outcome in outcomes
            ],
        )
        publish("ACTIVE")

        accepted_state_id = None
        if completed:
            final_account = self.broker.get_account()
            final_positions = self.broker.get_positions()
            final_position_facts = []
            for broker_position in final_positions:
                iid = instrument_id_for_symbol(broker_position.symbol)
                self.persistence._ensure_equity(
                    instrument_id=iid,
                    symbol=broker_position.symbol,
                )
                final_position_facts.append({
                    "financial_instrument_id": iid,
                    "quantity": broker_position.quantity,
                    "average_cost": broker_position.average_entry_price,
                    "market_value": broker_position.market_value,
                    "currency": "USD",
                })
            self.session.commit()

            accepted_state_id = self.persistence.portfolio_states.persist_broker_confirmed_state(
                portfolio_id=portfolio_id,
                prior_portfolio_state_id=initial_state_id,
                source_portfolio_decision_id=decision.portfolio_decision_id,
                configuration_version_id=config_id,
                cash=float(final_account.cash),
                equity=float(final_account.equity),
                buying_power=float(final_account.buying_power),
                positions=final_position_facts,
            )
            self.persistence.trace.add_lineage(
                flow_id=flow_id,
                parent_entity_type="PMA_Portfolio_Decision",
                parent_entity_id=decision.portfolio_decision_id,
                child_entity_type="PMA_Portfolio_State",
                child_entity_id=accepted_state_id,
                relationship_type="REALIZED_AS",
                sequence_number=4,
            )
            self.persistence.complete_flow(flow_id, status="COMPLETED")
            visibility.stage(
                "ACCEPTED PORTFOLIO STATE",
                status="ACCEPTED",
                portfolio_state_id=accepted_state_id,
                account_equity=_round_or_none(final_account.equity),
                cash=_round_or_none(final_account.cash),
                buying_power=_round_or_none(final_account.buying_power),
                positions=[
                    {
                        "symbol": broker_position.symbol,
                        "quantity": _round_or_none(broker_position.quantity),
                        "market_value": _round_or_none(broker_position.market_value),
                        "average_cost": _round_or_none(broker_position.average_entry_price),
                    }
                    for broker_position in final_positions
                ],
            )
        else:
            self.persistence.complete_flow(flow_id, status="SUSPENDED")
            visibility.stage(
                "ACCEPTED PORTFOLIO STATE",
                status="NOT_ACCEPTED",
                reason=(
                    "Execution was not broker-confirmed and verified. Recover the same flow; "
                    "do not originate a second flow."
                ),
            )

        report = publish("COMPLETED" if completed else "SUSPENDED_REQUIRES_RECOVERY")
        return ProductionPaperFlowResult(
            symbol=symbol,
            flow_id=flow_id,
            assessment_id=assessment.assessment_id,
            portfolio_decision_id=decision.portfolio_decision_id,
            validation_result_id=validation.validation_result_id,
            execution_ids=tuple(s.execution_id for s in states),
            completed=completed,
            accepted_portfolio_state_id=accepted_state_id,
            visibility_report=report,
        )
