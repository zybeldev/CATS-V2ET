"""Step 05B: gpt-oss-20b comparative TAA evaluation.

Uses the exact POSITIVE, NEGATIVE, and AMBIGUOUS evidence cases established in
Qwen Step 04D and the same explicit confidence semantics introduced in Step 04E.
The core TAA and Assessment contract are unchanged.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

import qwen_rag_grounding_evaluation as step04d
from qwen_confidence_calibration_evaluation import CONFIDENCE_CALIBRATION_RULE
from cats.adapters.llm import RemoteGptOssReasoningAdapter


NUMERIC_CONFIDENCE_CONTRACT_RULE = (
    "Existing Assessment contract clarification: confidence must be a JSON number "
    "between 0.0 and 1.0 inclusive, or null when confidence is unavailable. "
    "Do not return qualitative labels such as low, medium, or high for confidence."
)


class ConfidenceCalibrationWrapper:
    def __init__(self, delegate):
        self.delegate = delegate

    @property
    def last_metrics(self):
        return self.delegate.last_metrics

    def reason(self, *, task: str, context: dict) -> dict:
        return self.delegate.reason(
            task=(
                f"{task}\n\n{CONFIDENCE_CALIBRATION_RULE}"
                f"\n\n{NUMERIC_CONFIDENCE_CONTRACT_RULE}"
            ),
            context=context,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument(
        "--session-token",
        default=os.getenv("CATS_GPT_OSS_SESSION_TOKEN"),
        help="Temporary Colab token; defaults to CATS_GPT_OSS_SESSION_TOKEN.",
    )
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default="low")
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument(
        "--qwen-baseline-json",
        default="CATS_V2ET_Step_04E_Confidence_Calibration_Result.json",
    )
    parser.add_argument(
        "--output-json",
        default="CATS_V2ET_Step_05B_gpt_oss_TAA_Comparative_Result.json",
    )
    return parser.parse_args()


def _confidence(results: list[dict]) -> dict[str, float | None]:
    return {result["case"].lower(): step04d.confidence_of(result) for result in results}


def _calibration_pass(values: dict[str, float | None]) -> bool | None:
    positive = values.get("positive")
    negative = values.get("negative")
    ambiguous = values.get("ambiguous")
    if None in (positive, negative, ambiguous):
        return None
    return bool(ambiguous <= positive and ambiguous <= negative)


def _load_qwen_baseline(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "confidence": payload.get("confidence_after_calibration"),
        "calibration_check": payload.get("calibration_check"),
    }


def print_case(result: dict) -> None:
    assessment = result["assessment"]
    print("\n" + "=" * 78)
    print(f"CASE: {result['case']}")
    print(f"Evidence character: {result['evidence_character']}")
    print("-" * 78)
    for index, evidence in enumerate(result["evidence"], start=1):
        print(f"Evidence {index}: {evidence['text']}")
    print("-" * 78)
    print("Assessment summary:")
    print(assessment["summary"])
    print(f"Confidence: {assessment.get('confidence')}")
    print(
        "Evidence IDs preserved: "
        f"{result['hard_checks']['evidence_item_ids_match_case_documents']}"
    )
    if result.get("metrics") is not None:
        print("Remote gpt-oss metrics:")
        print(json.dumps(result["metrics"], indent=2))


def main() -> None:
    args = parse_args()
    if not args.session_token:
        raise SystemExit(
            "Missing session token. Set CATS_GPT_OSS_SESSION_TOKEN or pass --session-token."
        )

    instrument_id = uuid4()
    measurement_set_id = uuid4()
    configuration_version_id = uuid4()
    measurements = step04d.neutral_measurements()

    remote = RemoteGptOssReasoningAdapter(
        endpoint_url=args.endpoint_url,
        session_token=args.session_token,
        reasoning_effort=args.reasoning_effort,
        max_new_tokens=args.max_new_tokens,
        timeout_seconds=args.timeout_seconds,
    )
    reasoning = ConfidenceCalibrationWrapper(remote)

    results: list[dict] = []
    for case in step04d.CASES:
        result = step04d.run_case(
            case=case,
            instrument_id=instrument_id,
            measurement_set_id=measurement_set_id,
            configuration_version_id=configuration_version_id,
            measurements=measurements,
            reasoning=reasoning,
        )
        results.append(result)
        print_case(result)

    confidence = _confidence(results)
    calibration = _calibration_pass(confidence)
    qwen_baseline = _load_qwen_baseline(Path(args.qwen_baseline_json))

    report = {
        "experiment": "CATS V2ET Step 05B - gpt-oss-20b TAA Comparative Evaluation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope_boundary": {
            "core_taa_modified": False,
            "assessment_contract_modified": False,
            "retrieval_cases_changed_from_step04d": False,
            "confidence_semantics_changed_from_step04e": False,
            "existing_numeric_confidence_type_made_explicit": True,
            "model_under_test": "openai/gpt-oss-20b",
        },
        "controlled_variables": {
            "symbol": "ACME",
            "horizon": "TACTICAL",
            "assessment_type": "CANDIDATE",
            "query_text": step04d.QUERY_TEXT,
            "tss_measurements": asdict(measurements),
            "reasoning_effort": args.reasoning_effort,
            "variable_under_test": "reasoning model",
        },
        "confidence_calibration_rule": CONFIDENCE_CALIBRATION_RULE,
        "numeric_confidence_contract_rule": NUMERIC_CONFIDENCE_CONTRACT_RULE,
        "cases": results,
        "confidence": confidence,
        "calibration_check": {
            "ambiguous_not_higher_than_both_directional_cases": calibration,
        },
        "qwen_step04e_baseline": qwen_baseline,
    }

    output_path = Path(args.output_json)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("STEP 05B EXECUTION: COMPLETE")
    print("Hard contract/evidence-ID checks:")
    for result in results:
        checks = result["hard_checks"]
        print(
            f"  {result['case']}: contract=PASS, "
            f"evidence_ids={'PASS' if checks['evidence_item_ids_match_case_documents'] else 'FAIL'}"
        )
    print("gpt-oss confidence:")
    print(json.dumps(confidence, indent=2))
    print(
        "Calibration check: "
        + ("PASS" if calibration is True else "FAIL" if calibration is False else "UNAVAILABLE")
    )
    if qwen_baseline is not None:
        print("Qwen Step 04E baseline:")
        print(json.dumps(qwen_baseline, indent=2))
    print("\nManual semantic grounding review still required.")
    print(f"Saved evaluation record: {output_path}")


if __name__ == "__main__":
    main()
