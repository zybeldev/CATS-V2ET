"""Local V2ET TAA -> remote Colab Qwen -> Assessment smoke test.

Uses synthetic evidence only. The remote endpoint and short-lived session token
come from the Step 04C Colab server cell. No broker or commercial-model API is
used.
"""

from __future__ import annotations

import argparse
import json
import os
from uuid import uuid4

from cats.adapters.llm import RemoteQwenReasoningAdapter
from cats.agents.taa import TradingAssessmentAgent
from cats.retrieval import EvidenceDocument, InMemoryVectorStore, RetrievalService
from cats.retrieval.testing import DeterministicHashEmbeddingProvider
from cats.services.tss import EquityBar, TradingSignalService


def build_synthetic_retrieval(instrument_id):
    retrieval = RetrievalService(
        DeterministicHashEmbeddingProvider(),
        InMemoryVectorStore(),
    )
    retrieval.index(
        [
            EvidenceDocument(
                text=(
                    "Synthetic public-style earnings evidence: revenue increased, "
                    "operating margin improved, and management maintained guidance."
                ),
                source_name="Synthetic Earnings Release",
                external_reference="synthetic://earnings-release",
                financial_instrument_id=instrument_id,
            ),
            EvidenceDocument(
                text=(
                    "Synthetic public-style risk evidence: management identified "
                    "continued demand uncertainty in the next reporting period."
                ),
                source_name="Synthetic Investor Update",
                external_reference="synthetic://investor-update",
                financial_instrument_id=instrument_id,
            ),
        ]
    )
    return retrieval


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument(
        "--session-token",
        default=os.getenv("CATS_QWEN_SESSION_TOKEN"),
        help="Temporary Colab session token; defaults to CATS_QWEN_SESSION_TOKEN.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.session_token:
        raise SystemExit(
            "Missing session token. Set CATS_QWEN_SESSION_TOKEN or pass --session-token."
        )

    instrument_id = uuid4()
    bars = [EquityBar(close=100 + i, volume=1_000_000 + i * 1_000) for i in range(25)]
    measurements = TradingSignalService().calculate_equity_measurements(bars)

    reasoning = RemoteQwenReasoningAdapter(
        endpoint_url=args.endpoint_url,
        session_token=args.session_token,
        enable_thinking=False,
        max_new_tokens=256,
        timeout_seconds=args.timeout_seconds,
    )
    taa = TradingAssessmentAgent(
        retrieval=build_synthetic_retrieval(instrument_id),
        reasoning_model=reasoning,
    )

    assessment = taa.assess_equity(
        flow_id=uuid4(),
        financial_instrument_id=instrument_id,
        symbol="ACME",
        horizon="TACTICAL",
        assessment_type="CANDIDATE",
        query_text="revenue operating margin guidance demand uncertainty",
        tss_measurements=measurements,
        tss_measurement_set_id=uuid4(),
        configuration_version_id=uuid4(),
        top_k=2,
    )

    print("LOCAL TAA -> REMOTE QWEN -> ASSESSMENT: PASS")
    print(assessment.model_dump_json(indent=2))
    if reasoning.last_metrics is not None:
        print("\nRemote Qwen metrics:")
        print(json.dumps(reasoning.last_metrics.__dict__, indent=2))


if __name__ == "__main__":
    main()
