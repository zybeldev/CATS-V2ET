"""Real Qwen -> TAA -> RAG -> Assessment smoke test for a GPU runtime.

Uses synthetic/public-style evidence only. No broker account, API key, or external
service is required. Run in Colab or another compatible GPU environment after
installing the V2ET qwen optional dependencies.
"""

from __future__ import annotations

import json
from uuid import uuid4

from cats.adapters.llm import QwenReasoningAdapter
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


def main():
    instrument_id = uuid4()
    bars = [EquityBar(close=100 + i, volume=1_000_000 + i * 1_000) for i in range(25)]
    measurements = TradingSignalService().calculate_equity_measurements(bars)

    reasoning = QwenReasoningAdapter.from_pretrained(
        model_id="Qwen/Qwen3-14B-AWQ",
        enable_thinking=False,
        max_new_tokens=256,
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

    print("QWEN -> TAA ASSESSMENT: PASS")
    print(assessment.model_dump_json(indent=2))
    if reasoning.last_metrics is not None:
        print("\nQwen inference metrics:")
        print(json.dumps(reasoning.last_metrics.__dict__, indent=2))


if __name__ == "__main__":
    main()
