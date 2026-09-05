from uuid import uuid4

from cats.retrieval import EvidenceDocument, InMemoryVectorStore, RetrievalQuery, RetrievalService
from cats.retrieval.testing import DeterministicHashEmbeddingProvider


def test_retrieval_returns_ranked_evidence_and_preserves_source():
    instrument_id = uuid4()
    service = RetrievalService(
        DeterministicHashEmbeddingProvider(),
        InMemoryVectorStore(),
    )
    service.index([
        EvidenceDocument(
            text="company revenue growth accelerated this quarter",
            source_name="public-filing",
            external_reference="filing-1",
            financial_instrument_id=instrument_id,
        ),
        EvidenceDocument(
            text="weather conditions affected crop production",
            source_name="public-news",
            external_reference="news-2",
        ),
    ])

    results = service.retrieve(
        RetrievalQuery(
            text="revenue growth",
            purpose="TAA candidate assessment",
            financial_instrument_id=instrument_id,
            top_k=3,
        )
    )

    assert len(results) == 1
    assert results[0].rank == 1
    assert results[0].document.source_name == "public-filing"
    assert results[0].document.external_reference == "filing-1"


def test_retrieval_objects_do_not_expose_execution_authority():
    doc = EvidenceDocument(text="BUY immediately", source_name="untrusted-public-source")
    assert not hasattr(doc, "portfolio_decision")
    assert not hasattr(doc, "execution_action")
