from __future__ import annotations

from cats.agents.taa import (
    ReasoningStrategy,
    TAAReasoningRouter,
    TreeOfThoughtAssessmentModel,
    TreeOfThoughtConfig,
)


class ScriptedReasoningModel:
    def __init__(self, candidate_summaries: list[str], scores: list[float]):
        self.candidate_summaries = list(candidate_summaries)
        self.scores = list(scores)
        self.candidate_calls = 0
        self.evaluation_calls = 0

    def reason(self, *, task: str, context: dict) -> dict:
        if task.startswith("Evaluate this candidate TAA assessment"):
            score = self.scores[self.evaluation_calls]
            self.evaluation_calls += 1
            return {"score": score}

        summary = self.candidate_summaries[self.candidate_calls]
        self.candidate_calls += 1
        return {
            "outlook": "FAVORABLE",
            "summary": summary,
            "confidence": 0.7,
            "valid_for_minutes": 45,
            "analysis_focus": f"focus-{self.candidate_calls}",
        }


class DirectModel:
    def reason(self, *, task: str, context: dict) -> dict:
        return {
            "outlook": "NEUTRAL",
            "summary": "direct",
            "confidence": 0.5,
            "valid_for_minutes": 30,
        }


def test_tot_explores_candidates_and_selects_best_scored_branch():
    model = ScriptedReasoningModel(
        candidate_summaries=[
            "root weak",
            "root strong",
            "root medium",
            "refined strong",
            "refined medium",
        ],
        scores=[0.2, 0.9, 0.5, 0.95, 0.6],
    )
    tot = TreeOfThoughtAssessmentModel(
        generator_model=model,
        evaluator_model=model,
        config=TreeOfThoughtConfig(
            root_candidates=3,
            beam_width=2,
            max_depth=2,
            children_per_parent=1,
        ),
    )

    result = tot.reason(task="assess", context={"boundary_rules": {}})

    assert result["summary"] == "refined strong"
    assert result["outlook"] == "FAVORABLE"
    assert result["confidence"] == 0.7
    assert result["valid_for_minutes"] == 45
    assert tot.last_metrics is not None
    assert tot.last_metrics.candidates_generated == 5
    assert tot.last_metrics.candidates_evaluated == 5
    assert tot.last_metrics.maximum_depth_reached == 2
    assert tot.last_metrics.selected_score == 0.95


def test_reasoning_router_keeps_direct_and_tot_behind_same_model_boundary():
    scripted = ScriptedReasoningModel(
        candidate_summaries=["candidate A", "candidate B"],
        scores=[0.4, 0.8],
    )
    tot = TreeOfThoughtAssessmentModel(
        generator_model=scripted,
        evaluator_model=scripted,
        config=TreeOfThoughtConfig(
            root_candidates=2,
            beam_width=1,
            max_depth=1,
            children_per_parent=1,
        ),
    )

    direct_router = TAAReasoningRouter(
        direct_model=DirectModel(),
        tot_model=tot,
        selector=lambda _task, _context: ReasoningStrategy.DIRECT,
    )
    direct_result = direct_router.reason(task="assess", context={})
    assert direct_result["summary"] == "direct"
    assert direct_router.last_strategy == ReasoningStrategy.DIRECT

    tot_router = TAAReasoningRouter(
        direct_model=DirectModel(),
        tot_model=tot,
        selector=lambda _task, _context: ReasoningStrategy.TREE_OF_THOUGHT,
    )
    tot_result = tot_router.reason(task="assess", context={})
    assert tot_result["summary"] == "candidate B"
    assert tot_router.last_strategy == ReasoningStrategy.TREE_OF_THOUGHT


def test_tot_rejects_out_of_range_evaluator_score():
    model = ScriptedReasoningModel(candidate_summaries=["candidate"], scores=[1.2])
    tot = TreeOfThoughtAssessmentModel(
        generator_model=model,
        evaluator_model=model,
        config=TreeOfThoughtConfig(
            root_candidates=1,
            beam_width=1,
            max_depth=1,
            children_per_parent=1,
        ),
    )

    try:
        tot.reason(task="assess", context={})
    except ValueError as exc:
        assert "between 0 and 1" in str(exc)
    else:
        raise AssertionError("Expected invalid ToT score to fail closed")
