"""Step 04E: bounded confidence-calibration experiment for remote Qwen TAA.

This experiment does not change the CATS TAA implementation or Assessment contract.
It wraps the existing remote reasoning model only inside this evaluation harness and
adds an explicit semantic definition of confidence to the task instruction.

The same POSITIVE, NEGATIVE, and AMBIGUOUS evidence cases from Step 04D are rerun.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import qwen_rag_grounding_evaluation as step04d
from cats.adapters.llm import RemoteQwenReasoningAdapter


CONFIDENCE_CALIBRATION_RULE = (
    "Confidence semantics for this experiment: confidence represents evidentiary "
    "certainty in the assessment, not confidence that the situation is uncertain. "
    "Use higher confidence only when the supplied evidence and deterministic "
    "measurements consistently support the assessment. Mixed, contradictory, "
    "limited, or insufficiently directional evidence must reduce confidence. "
    "Do not increase confidence merely because the conclusion itself is neutral, "
    "mixed, or uncertain."
)


class ConfidenceCalibrationWrapper:
    """Evaluation-only wrapper that clarifies confidence semantics.

    This wrapper deliberately sits outside the production TAA implementation. It
    changes only the task instruction presented to the same reasoning model.
    """

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate

    @property
    def last_metrics(self):
        return self.delegate.last_metrics

    def reason(self, *, task: str, context: dict) -> dict:
        calibrated_task = f"{task}\n\n{CONFIDENCE_CALIBRATION_RULE}"
        return self.delegate.reason(task=calibrated_task, context=context)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument(
        "--session-token",
        default=os.getenv("CATS_QWEN_SESSION_TOKEN"),
        help="Temporary Colab session token; defaults to CATS_QWEN_SESSION_TOKEN.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-new-tokens", type=int, default=320)
    parser.add_argument(
        "--baseline-json",
        default="CATS_V2ET_Step_04D_RAG_Grounding_Result.json",
        help="Optional Step 04D result used for before/after comparison.",
    )
    parser.add_argument(
        "--output-json",
        default="CATS_V2ET_Step_04E_Confidence_Calibration_Result.json",
    )
    return parser.parse_args()


def _confidence_map(results: list[dict]) -> dict[str, float | None]:
    return {
        result["case"].lower(): step04d.confidence_of(result)
        for result in results
    }


def _calibration_check(confidence: dict[str, float | None]) -> bool | None:
    positive = confidence.get("positive")
    negative = confidence.get("negative")
    ambiguous = confidence.get("ambiguous")
    if None in (positive, negative, ambiguous):
        return None
    return bool(ambiguous <= positive and ambiguous <= negative)


def _load_baseline(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    confidence = payload.get("cross_case_observations", {}).get("confidence")
    return confidence if isinstance(confidence, dict) else None


def main() -> None:
    args = parse_args()
    if not args.session_token:
        raise SystemExit(
            "Missing session token. Set CATS_QWEN_SESSION_TOKEN or pass --session-token."
        )

    instrument_id = uuid4()
    measurement_set_id = uuid4()
    configuration_version_id = uuid4()
    measurements = step04d.neutral_measurements()

    remote_model = RemoteQwenReasoningAdapter(
        endpoint_url=args.endpoint_url,
        session_token=args.session_token,
        enable_thinking=False,
        max_new_tokens=args.max_new_tokens,
        timeout_seconds=args.timeout_seconds,
    )
    calibrated_model = ConfidenceCalibrationWrapper(remote_model)

    results: list[dict] = []
    for case in step04d.CASES:
        result = step04d.run_case(
            case=case,
            instrument_id=instrument_id,
            measurement_set_id=measurement_set_id,
            configuration_version_id=configuration_version_id,
            measurements=measurements,
            reasoning=calibrated_model,
        )
        results.append(result)
        step04d.print_case(result)

    confidence = _confidence_map(results)
    calibration_pass = _calibration_check(confidence)
    baseline = _load_baseline(Path(args.baseline_json))

    report = {
        "experiment": "CATS V2ET Step 04E - Qwen Confidence Calibration Evaluation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope_boundary": {
            "core_taa_modified": False,
            "assessment_contract_modified": False,
            "model_changed": False,
            "retrieval_cases_changed": False,
            "only_experimental_task_semantics_changed": True,
        },
        "confidence_calibration_rule": CONFIDENCE_CALIBRATION_RULE,
        "controlled_variables": {
            "model": "Qwen/Qwen3-14B-AWQ",
            "thinking_enabled": False,
            "symbol": "ACME",
            "horizon": "TACTICAL",
            "assessment_type": "CANDIDATE",
            "query_text": step04d.QUERY_TEXT,
            "tss_measurements": asdict(measurements),
            "variable_under_test": "explicit confidence semantics in the task instruction",
        },
        "cases": results,
        "confidence_after_calibration": confidence,
        "calibration_check": {
            "ambiguous_not_higher_than_both_directional_cases": calibration_pass,
        },
        "step04d_baseline_confidence": baseline,
    }

    output_path = Path(args.output_json)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("STEP 04E EXECUTION: COMPLETE")
    print("Experimental boundary: core TAA unchanged; only task semantics clarified.")
    print("Confidence after calibration:")
    print(json.dumps(confidence, indent=2))
    print(
        "Calibration check: "
        + ("PASS" if calibration_pass is True else "FAIL" if calibration_pass is False else "UNAVAILABLE")
    )
    if baseline is not None:
        print("Step 04D baseline confidence:")
        print(json.dumps(baseline, indent=2))
    print(f"Saved evaluation record: {output_path}")


if __name__ == "__main__":
    main()
