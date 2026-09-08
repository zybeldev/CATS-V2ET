from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from cats.agents.pma import PortfolioManagementAgent, PortfolioStateView
from cats.agents.tea import TradingExecutionAgent
from cats.contracts import Assessment, PortfolioDecision, ValidationResult
from cats.systems.sys import GovernedConfiguration, SystemValidator, ValidationContext


class CATSBackboneState(TypedDict, total=False):
    """LangGraph control state for the bounded V2ET backbone experiment.

    The graph carries identifiers and control indicators only. CATS domain objects
    stay in the run context and remain owned by their existing components.
    """

    flow_id: str
    current_state: str
    assessment_id: str
    portfolio_decision_id: str
    validation_result_id: str
    execution_ids: tuple[str, ...]
    completed: bool
    terminal_state: str
    terminal_reason: str
    path: tuple[str, ...]


@dataclass
class _RunContext:
    assessment: Assessment
    portfolio_state: PortfolioStateView
    strategic_envelope_id: UUID
    configuration_version_id: UUID
    governed_config: GovernedConfiguration
    validation_context: ValidationContext
    symbol_by_instrument: dict[UUID, str]
    optimization_inputs: dict | None
    decision: PortfolioDecision | None = None
    validation: ValidationResult | None = None


@dataclass(frozen=True)
class LangGraphVerticalSliceResult:
    assessment_id: UUID
    portfolio_decision_id: UUID
    validation_result_id: UUID
    execution_ids: tuple[UUID, ...]
    completed: bool
    terminal_state: str
    terminal_reason: str
    path: tuple[str, ...]


def _require_langgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised by operator setup
        raise RuntimeError(
            'LangGraph support is optional. Install it with: pip install -e ".[dev,langgraph]"'
        ) from exc
    return StateGraph, START, END


def _append_path(state: CATSBackboneState, node: str) -> tuple[str, ...]:
    return (*state.get("path", ()), node)


class LangGraphV2ETOrchestrator:
    """LangGraph variation of the V2ET vertical-slice coordinator.

    LangGraph owns only runtime state transitions and principal-component flow.
    PMA, SYS, TEA, PMS, TES, contracts, and financial authority remain unchanged.

    The entry contract is an existing TAA ``Assessment``. The TAA graph node is
    therefore an ingress/material-boundary marker; it does not invoke TAA reasoning
    a second time. PMS remains called through PMA's existing optimizer boundary and
    TES remains called through TEA's existing execution boundary.
    """

    def __init__(
        self,
        *,
        pma: PortfolioManagementAgent,
        sys_validator: SystemValidator,
        tea: TradingExecutionAgent,
        trace=None,
    ):
        self.pma = pma
        self.sys_validator = sys_validator
        self.tea = tea
        self.trace = trace

    def _build_graph(self, context: _RunContext):
        StateGraph, START, END = _require_langgraph()

        def taa_material(state: CATSBackboneState):
            return {
                "current_state": "TAA_MATERIAL_READY",
                "assessment_id": str(context.assessment.assessment_id),
                "path": _append_path(state, "TAA"),
            }

        def pma_decision(state: CATSBackboneState):
            context.decision = self.pma.decide(
                assessment=context.assessment,
                portfolio_state=context.portfolio_state,
                strategic_envelope_id=context.strategic_envelope_id,
                configuration_version_id=context.configuration_version_id,
                optimization_inputs=context.optimization_inputs,
            )
            return {
                "current_state": "PMA_DECISION_READY",
                "portfolio_decision_id": str(context.decision.portfolio_decision_id),
                "path": _append_path(state, "PMA"),
            }

        def sys_validation(state: CATSBackboneState):
            if context.decision is None:
                raise RuntimeError("PMA decision is required before SYS validation.")
            context.validation = self.sys_validator.validate(
                context.decision,
                context.governed_config,
                context.validation_context,
            )
            return {
                "current_state": (
                    "SYS_PASS" if context.validation.result == "PASS" else "SYS_FAIL"
                ),
                "validation_result_id": str(context.validation.validation_result_id),
                "path": _append_path(state, "SYS"),
            }

        def route_after_sys(state: CATSBackboneState):
            if context.decision is None or context.validation is None:
                raise RuntimeError("SYS routing requires PMA decision and validation result.")
            if context.validation.result != "PASS":
                return "complete"
            if context.decision.decision_type == "NO_CHANGE":
                return "complete"
            return "tea"

        def tea_execution(state: CATSBackboneState):
            if context.decision is None or context.validation is None:
                raise RuntimeError("TEA execution requires validated PMA intent.")

            states = self.tea.start_execution(
                decision=context.decision,
                validation=context.validation,
                symbol_by_instrument=context.symbol_by_instrument,
            )

            completed = True
            for execution_state in states:
                self.tea.run_cycle(state=execution_state)
                final = self.tea.run_cycle(state=execution_state)
                completed = completed and bool(final and getattr(final, "verified", False))

            return {
                "current_state": "TEA_EXECUTION_COMPLETE" if completed else "TEA_SUSPENDED",
                "execution_ids": tuple(str(item.execution_id) for item in states),
                "completed": completed,
                "path": _append_path(state, "TEA"),
            }

        def route_after_tea(state: CATSBackboneState):
            return "complete" if state.get("completed", False) else "suspended"

        def complete(state: CATSBackboneState):
            if context.validation is not None and context.validation.result != "PASS":
                reason = "SYS_REJECTED"
            elif context.decision is not None and context.decision.decision_type == "NO_CHANGE":
                reason = "NO_CHANGE"
            else:
                reason = "EXECUTION_VERIFIED"
            return {
                "current_state": "COMPLETED",
                "terminal_state": "COMPLETED",
                "terminal_reason": reason,
                "completed": True,
                "path": _append_path(state, "COMPLETED"),
            }

        def suspended(state: CATSBackboneState):
            return {
                "current_state": "SUSPENDED",
                "terminal_state": "SUSPENDED",
                "terminal_reason": "EXECUTION_NOT_VERIFIED",
                "completed": False,
                "path": _append_path(state, "SUSPENDED"),
            }

        builder = StateGraph(CATSBackboneState)
        builder.add_node("taa", taa_material)
        builder.add_node("pma", pma_decision)
        builder.add_node("sys", sys_validation)
        builder.add_node("tea", tea_execution)
        builder.add_node("complete", complete)
        builder.add_node("suspended", suspended)

        builder.add_edge(START, "taa")
        builder.add_edge("taa", "pma")
        builder.add_edge("pma", "sys")
        builder.add_conditional_edges(
            "sys",
            route_after_sys,
            {"tea": "tea", "complete": "complete"},
        )
        builder.add_conditional_edges(
            "tea",
            route_after_tea,
            {"complete": "complete", "suspended": "suspended"},
        )
        builder.add_edge("complete", END)
        builder.add_edge("suspended", END)
        return builder.compile()

    def run_from_assessment(
        self,
        *,
        assessment: Assessment,
        portfolio_state: PortfolioStateView,
        strategic_envelope_id: UUID,
        configuration_version_id: UUID,
        governed_config: GovernedConfiguration,
        validation_context: ValidationContext,
        symbol_by_instrument: dict[UUID, str],
        optimization_inputs: dict | None = None,
    ) -> LangGraphVerticalSliceResult:
        context = _RunContext(
            assessment=assessment,
            portfolio_state=portfolio_state,
            strategic_envelope_id=strategic_envelope_id,
            configuration_version_id=configuration_version_id,
            governed_config=governed_config,
            validation_context=validation_context,
            symbol_by_instrument=symbol_by_instrument,
            optimization_inputs=optimization_inputs,
        )
        graph = self._build_graph(context)
        state = graph.invoke(
            {
                "flow_id": str(assessment.flow_id),
                "current_state": "READY",
                "assessment_id": str(assessment.assessment_id),
                "execution_ids": (),
                "completed": False,
                "path": (),
            }
        )

        if context.decision is None or context.validation is None:
            raise RuntimeError("LangGraph flow ended before PMA/SYS material was produced.")

        return LangGraphVerticalSliceResult(
            assessment_id=assessment.assessment_id,
            portfolio_decision_id=context.decision.portfolio_decision_id,
            validation_result_id=context.validation.validation_result_id,
            execution_ids=tuple(UUID(item) for item in state.get("execution_ids", ())),
            completed=bool(state.get("completed", False)),
            terminal_state=state.get("terminal_state", "UNKNOWN"),
            terminal_reason=state.get("terminal_reason", "UNKNOWN"),
            path=tuple(state.get("path", ())),
        )
