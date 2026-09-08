from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from cats.adapters.llm import StructuredReasoningModel


class ReasoningStrategy(str, Enum):
    """Reasoning strategies available inside TAA.

    This is an internal TAA mechanism. Selecting a strategy does not change
    TAA authority, inputs, or the Assessment contract returned to PMA.
    """

    DIRECT = "DIRECT"
    TREE_OF_THOUGHT = "TREE_OF_THOUGHT"


@dataclass(frozen=True)
class TreeOfThoughtConfig:
    """Bounded search budget for TAA Tree-of-Thought reasoning."""

    root_candidates: int = 3
    beam_width: int = 2
    max_depth: int = 2
    children_per_parent: int = 1

    def __post_init__(self) -> None:
        for name, value in (
            ("root_candidates", self.root_candidates),
            ("beam_width", self.beam_width),
            ("max_depth", self.max_depth),
            ("children_per_parent", self.children_per_parent),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class CandidateAssessment:
    """A structured candidate assessment explored by the ToT controller.

    The candidate stores an externally auditable assessment hypothesis, not a
    hidden chain-of-thought transcript.
    """

    candidate_id: int
    outlook: str
    summary: str
    confidence: float | None
    valid_for_minutes: int
    analysis_focus: str
    depth: int
    parent_candidate_id: int | None = None
    score: float | None = None


@dataclass(frozen=True)
class TreeOfThoughtMetrics:
    candidates_generated: int
    candidates_evaluated: int
    maximum_depth_reached: int
    selected_candidate_id: int
    selected_score: float


class TreeOfThoughtAssessmentModel:
    """Bounded Tree-of-Thought controller for TAA assessment reasoning.

    Course influence: candidate generation, explicit evaluation/ranking, and
    bounded beam-style search. CATS adaptation: branches are structured
    candidate financial assessments and the controller returns the same
    dictionary expected by the existing TAA Assessment boundary.
    """

    def __init__(
        self,
        *,
        generator_model: StructuredReasoningModel,
        evaluator_model: StructuredReasoningModel | None = None,
        config: TreeOfThoughtConfig | None = None,
    ) -> None:
        self.generator_model = generator_model
        self.evaluator_model = evaluator_model or generator_model
        self.config = config or TreeOfThoughtConfig()
        self.last_metrics: TreeOfThoughtMetrics | None = None
        self._next_candidate_id = 1

    def reason(self, *, task: str, context: dict) -> dict:
        self.last_metrics = None
        self._next_candidate_id = 1
        generated_count = 0
        evaluated_count = 0
        max_depth_reached = 1

        root_candidates = [
            self._generate_candidate(
                original_task=task,
                context=context,
                depth=1,
                parent=None,
            )
            for _ in range(self.config.root_candidates)
        ]
        generated_count += len(root_candidates)

        frontier = self._evaluate_candidates(
            original_task=task,
            context=context,
            candidates=root_candidates,
        )
        evaluated_count += len(frontier)
        frontier = self._select_frontier(frontier)

        for depth in range(2, self.config.max_depth + 1):
            expanded: list[CandidateAssessment] = []
            for parent in frontier:
                for _ in range(self.config.children_per_parent):
                    expanded.append(
                        self._generate_candidate(
                            original_task=task,
                            context=context,
                            depth=depth,
                            parent=parent,
                        )
                    )

            if not expanded:
                break

            generated_count += len(expanded)
            max_depth_reached = depth
            evaluated = self._evaluate_candidates(
                original_task=task,
                context=context,
                candidates=expanded,
            )
            evaluated_count += len(evaluated)
            frontier = self._select_frontier(evaluated)

        if not frontier:
            raise ValueError("Tree-of-Thought reasoning produced no valid candidate assessments")

        selected = max(frontier, key=lambda candidate: (candidate.score or 0.0, -candidate.candidate_id))
        selected_score = 0.0 if selected.score is None else selected.score
        self.last_metrics = TreeOfThoughtMetrics(
            candidates_generated=generated_count,
            candidates_evaluated=evaluated_count,
            maximum_depth_reached=max_depth_reached,
            selected_candidate_id=selected.candidate_id,
            selected_score=selected_score,
        )

        return {
            "outlook": selected.outlook,
            "summary": selected.summary,
            "confidence": selected.confidence,
            "valid_for_minutes": selected.valid_for_minutes,
        }

    def _generate_candidate(
        self,
        *,
        original_task: str,
        context: dict,
        depth: int,
        parent: CandidateAssessment | None,
    ) -> CandidateAssessment:
        generation_context = dict(context)
        if parent is not None:
            generation_context = {
                **generation_context,
                "candidate_to_stress_test": {
                    "outlook": parent.outlook,
                    "summary": parent.summary,
                    "confidence": parent.confidence,
                    "analysis_focus": parent.analysis_focus,
                    "score": parent.score,
                },
            }

        if parent is None:
            task = (
                "Generate one independent candidate financial assessment for a bounded "
                "Tree-of-Thought search. Use only supplied evidence and deterministic "
                "measurements. Return JSON fields: outlook, summary, confidence, "
                "valid_for_minutes, analysis_focus. Outlook must be FAVORABLE, NEUTRAL, "
                "or ADVERSE. Do not issue portfolio intent or "
                "execution actions. Original TAA task: "
                f"{original_task}"
            )
        else:
            task = (
                "Generate one improved candidate financial assessment by stress-testing "
                "the supplied candidate against the authoritative context, retrieved "
                "evidence, and deterministic measurements. Return JSON fields: outlook, "
                "summary, confidence, valid_for_minutes, analysis_focus. Outlook must be "
                "FAVORABLE, NEUTRAL, or ADVERSE. Do not issue portfolio "
                "intent or execution actions. Original TAA task: "
                f"{original_task}"
            )

        raw = self.generator_model.reason(task=task, context=generation_context)
        candidate = self._parse_candidate(raw, depth=depth, parent=parent)
        return candidate

    def _evaluate_candidates(
        self,
        *,
        original_task: str,
        context: dict,
        candidates: list[CandidateAssessment],
    ) -> list[CandidateAssessment]:
        evaluated: list[CandidateAssessment] = []
        for candidate in candidates:
            evaluation_context = {
                **context,
                "candidate_assessment": {
                    "outlook": candidate.outlook,
                    "summary": candidate.summary,
                    "confidence": candidate.confidence,
                    "analysis_focus": candidate.analysis_focus,
                    "depth": candidate.depth,
                },
            }
            raw = self.evaluator_model.reason(
                task=(
                    "Evaluate this candidate TAA assessment for evidence grounding, "
                    "consistency with deterministic measurements, uncertainty calibration, "
                    "relevance to the original task, and compliance with TAA authority. "
                    "Return JSON with one numeric field score between 0 and 1. "
                    f"Original TAA task: {original_task}"
                ),
                context=evaluation_context,
            )
            score = self._parse_score(raw)
            evaluated.append(
                CandidateAssessment(
                    candidate_id=candidate.candidate_id,
                    outlook=candidate.outlook,
                    summary=candidate.summary,
                    confidence=candidate.confidence,
                    valid_for_minutes=candidate.valid_for_minutes,
                    analysis_focus=candidate.analysis_focus,
                    depth=candidate.depth,
                    parent_candidate_id=candidate.parent_candidate_id,
                    score=score,
                )
            )
        return evaluated

    def _select_frontier(self, candidates: list[CandidateAssessment]) -> list[CandidateAssessment]:
        return sorted(
            candidates,
            key=lambda candidate: (-(candidate.score or 0.0), candidate.candidate_id),
        )[: self.config.beam_width]

    def _parse_candidate(
        self,
        raw: dict,
        *,
        depth: int,
        parent: CandidateAssessment | None,
    ) -> CandidateAssessment:
        outlook = str(raw.get("outlook", "")).strip().upper()
        if outlook not in {"FAVORABLE", "NEUTRAL", "ADVERSE"}:
            raise ValueError("ToT generator must return outlook FAVORABLE, NEUTRAL, or ADVERSE")

        summary = str(raw.get("summary", "")).strip()
        if not summary:
            raise ValueError("ToT generator returned an empty candidate summary")

        confidence_raw = raw.get("confidence")
        confidence = None if confidence_raw is None else float(confidence_raw)
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("ToT candidate confidence must be between 0 and 1")

        valid_for_minutes = max(1, int(raw.get("valid_for_minutes", 60)))
        analysis_focus = str(raw.get("analysis_focus", "general")).strip() or "general"

        candidate = CandidateAssessment(
            candidate_id=self._next_candidate_id,
            outlook=outlook,
            summary=summary,
            confidence=confidence,
            valid_for_minutes=valid_for_minutes,
            analysis_focus=analysis_focus,
            depth=depth,
            parent_candidate_id=None if parent is None else parent.candidate_id,
        )
        self._next_candidate_id += 1
        return candidate

    @staticmethod
    def _parse_score(raw: dict) -> float:
        if "score" not in raw:
            raise ValueError("ToT evaluator did not return a score")
        score = float(raw["score"])
        if not 0 <= score <= 1:
            raise ValueError("ToT evaluator score must be between 0 and 1")
        return score


ReasoningSelector = Callable[[str, dict], ReasoningStrategy]


class TAAReasoningRouter:
    """Select direct or ToT reasoning without changing the TAA contract."""

    def __init__(
        self,
        *,
        direct_model: StructuredReasoningModel,
        tot_model: TreeOfThoughtAssessmentModel,
        selector: ReasoningSelector | None = None,
    ) -> None:
        self.direct_model = direct_model
        self.tot_model = tot_model
        self.selector = selector or (lambda _task, _context: ReasoningStrategy.DIRECT)
        self.last_strategy: ReasoningStrategy | None = None

    def reason(self, *, task: str, context: dict) -> dict:
        strategy = self.selector(task, context)
        self.last_strategy = strategy
        if strategy == ReasoningStrategy.DIRECT:
            return self.direct_model.reason(task=task, context=context)
        if strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            return self.tot_model.reason(task=task, context=context)
        raise ValueError(f"Unsupported TAA reasoning strategy: {strategy}")
