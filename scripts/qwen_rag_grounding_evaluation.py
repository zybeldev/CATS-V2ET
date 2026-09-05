"""Step 04D: controlled RAG-grounding evaluation for remote Qwen TAA.

Runs three synthetic evidence conditions while holding the instrument, deterministic
TSS measurements, TAA contract, query, model configuration, and endpoint constant.
Only the retrieved evidence changes.

This is an evaluation script, not a production trading workflow.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4

from cats.adapters.llm import RemoteQwenReasoningAdapter
from cats.agents.taa import TradingAssessmentAgent
from cats.retrieval import EvidenceDocument, InMemoryVectorStore, RetrievalService
from cats.retrieval.testing import DeterministicHashEmbeddingProvider
from cats.services.tss import EquityBar, TradingSignalService


@dataclass(frozen=True)
class GroundingCase:
    name: str
    evidence_character: str
    documents: tuple[str, ...]


CASES = (
    GroundingCase(
        name="POSITIVE",
        evidence_character="clearly positive operating evidence",
        documents=(
            "Synthetic evidence: quarterly revenue increased 14 percent year over year, "
            "operating margin expanded by 3 percentage points, and management raised full-year guidance.",
            "Synthetic evidence: customer orders accelerated during the quarter and management "
            "reported stronger demand across its largest business segment.",
        ),
    ),
    GroundingCase(
        name="NEGATIVE",
        evidence_character="clearly negative operating evidence",
        documents=(
            "Synthetic evidence: quarterly revenue declined 14 percent year over year, "
            "operating margin contracted by 3 percentage points, and management reduced full-year guidance.",
            "Synthetic evidence: customer cancellations increased during the quarter and management "
            "reported weaker demand across its largest business segment.",
        ),
    ),
    GroundingCase(
        name="AMBIGUOUS",
        evidence_character="mixed and insufficiently directional evidence",
        documents=(
            "Synthetic evidence: quarterly revenue was approximately flat year over year, "
            "operating margin was stable, and management maintained existing full-year guidance.",
            "Synthetic evidence: management reported mixed regional demand and stated that near-term "
            "visibility remains limited, with no clear change in overall customer order trends.",
        ),
    ),
)

QUERY_TEXT = "revenue operating margin guidance demand customer orders outlook"


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
        "--output-json",
        default="CATS_V2ET_Step_04D_RAG_Grounding_Result.json",
        help="Path for the machine-readable evaluation record.",
    )
    return parser.parse_args()


def neutral_measurements():
    """Return identical, intentionally neutral deterministic measurements for all cases."""
    bars = [EquityBar(close=100.0, volume=1_000_000.0) for _ in range(25)]
    return TradingSignalService().calculate_equity_measurements(bars)


def build_case_retrieval(
    *,
    case: GroundingCase,
    instrument_id: UUID,
) -> tuple[RetrievalService, list[EvidenceDocument]]:
    documents = [
        EvidenceDocument(
            text=text,
            source_name=f"Synthetic {case.name.title()} Evidence {index}",
            external_reference=f"synthetic://step04d/{case.name.lower()}/{index}",
            financial_instrument_id=instrument_id,
            metadata={"step": "04D", "case": case.name},
        )
        for index, text in enumerate(case.documents, start=1)
    ]
    retrieval = RetrievalService(
        DeterministicHashEmbeddingProvider(),
        InMemoryVectorStore(),
    )
    retrieval.index(documents)
    return retrieval, documents


def run_case(
    *,
    case: GroundingCase,
    instrument_id: UUID,
    measurement_set_id: UUID,
    configuration_version_id: UUID,
    measurements,
    reasoning: RemoteQwenReasoningAdapter,
) -> dict:
    retrieval, indexed_documents = build_case_retrieval(
        case=case,
        instrument_id=instrument_id,
    )
    taa = TradingAssessmentAgent(retrieval=retrieval, reasoning_model=reasoning)

    assessment = taa.assess_equity(
        flow_id=uuid4(),
        financial_instrument_id=instrument_id,
        symbol="ACME",
        horizon="TACTICAL",
        assessment_type="CANDIDATE",
        query_text=QUERY_TEXT,
        tss_measurements=measurements,
        tss_measurement_set_id=measurement_set_id,
        configuration_version_id=configuration_version_id,
        top_k=len(indexed_documents),
    )

    expected_ids = {str(document.evidence_document_id) for document in indexed_documents}
    actual_ids = {str(item) for item in assessment.evidence_item_ids}

    metrics = None
    if reasoning.last_metrics is not None:
        metrics = asdict(reasoning.last_metrics)

    return {
        "case": case.name,
        "evidence_character": case.evidence_character,
        "evidence": [
            {
                "evidence_document_id": str(document.evidence_document_id),
                "text": document.text,
                "source_name": document.source_name,
            }
            for document in indexed_documents
        ],
        "assessment": assessment.model_dump(mode="json"),
        "hard_checks": {
            "assessment_contract_valid": True,
            "evidence_item_ids_match_case_documents": actual_ids == expected_ids,
            "evidence_item_count": len(actual_ids),
        },
        "metrics": metrics,
    }


def confidence_of(case_result: dict) -> float | None:
    value = case_result["assessment"].get("confidence")
    return None if value is None else float(value)


def print_case(case_result: dict) -> None:
    assessment = case_result["assessment"]
    print("\n" + "=" * 78)
    print(f"CASE: {case_result['case']}")
    print(f"Evidence character: {case_result['evidence_character']}")
    print("-" * 78)
    for index, evidence in enumerate(case_result["evidence"], start=1):
        print(f"Evidence {index}: {evidence['text']}")
    print("-" * 78)
    print("Assessment summary:")
    print(assessment["summary"])
    print(f"Confidence: {assessment.get('confidence')}")
    print(
        "Evidence IDs preserved: "
        f"{case_result['hard_checks']['evidence_item_ids_match_case_documents']}"
    )
    if case_result["metrics"] is not None:
        print("Remote Qwen metrics:")
        print(json.dumps(case_result["metrics"], indent=2))


def main() -> None:
    args = parse_args()
    if not args.session_token:
        raise SystemExit(
            "Missing session token. Set CATS_QWEN_SESSION_TOKEN or pass --session-token."
        )

    instrument_id = uuid4()
    measurement_set_id = uuid4()
    configuration_version_id = uuid4()
    measurements = neutral_measurements()

    reasoning = RemoteQwenReasoningAdapter(
        endpoint_url=args.endpoint_url,
        session_token=args.session_token,
        enable_thinking=False,
        max_new_tokens=args.max_new_tokens,
        timeout_seconds=args.timeout_seconds,
    )

    results = []
    for case in CASES:
        result = run_case(
            case=case,
            instrument_id=instrument_id,
            measurement_set_id=measurement_set_id,
            configuration_version_id=configuration_version_id,
            measurements=measurements,
            reasoning=reasoning,
        )
        results.append(result)
        print_case(result)

    positive_confidence = confidence_of(results[0])
    negative_confidence = confidence_of(results[1])
    ambiguous_confidence = confidence_of(results[2])

    confidence_observation = None
    if None not in (positive_confidence, negative_confidence, ambiguous_confidence):
        confidence_observation = {
            "positive": positive_confidence,
            "negative": negative_confidence,
            "ambiguous": ambiguous_confidence,
            "ambiguous_not_higher_than_both_directional_cases": (
                ambiguous_confidence <= positive_confidence
                and ambiguous_confidence <= negative_confidence
            ),
        }

    report = {
        "experiment": "CATS V2ET Step 04D - Qwen RAG Grounding Evaluation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "controlled_variables": {
            "model": "Qwen/Qwen3-14B-AWQ",
            "thinking_enabled": False,
            "symbol": "ACME",
            "financial_instrument_id": str(instrument_id),
            "horizon": "TACTICAL",
            "assessment_type": "CANDIDATE",
            "query_text": QUERY_TEXT,
            "tss_measurements": asdict(measurements),
            "tss_measurement_set_id": str(measurement_set_id),
            "configuration_version_id": str(configuration_version_id),
            "variable_under_test": "retrieved evidence",
        },
        "cases": results,
        "cross_case_observations": {
            "confidence": confidence_observation,
            "manual_review_required": {
                "summary_changes_with_evidence": True,
                "summary_uses_supplied_evidence": True,
                "unsupported_factual_claims": True,
                "uncertainty_matches_ambiguous_evidence": True,
            },
        },
    }

    output_path = Path(args.output_json)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("STEP 04D EXECUTION: COMPLETE")
    print("Hard contract/evidence-ID checks:")
    for result in results:
        checks = result["hard_checks"]
        print(
            f"  {result['case']}: contract=PASS, "
            f"evidence_ids={'PASS' if checks['evidence_item_ids_match_case_documents'] else 'FAIL'}"
        )
    if confidence_observation is not None:
        print("Confidence observation:")
        print(json.dumps(confidence_observation, indent=2))
    print("\nManual grounding review still required for semantic quality.")
    print(f"Saved evaluation record: {output_path}")


if __name__ == "__main__":
    main()
