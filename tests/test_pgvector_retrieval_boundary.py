from uuid import uuid4

import pytest

from cats.retrieval import EvidenceDocument, RetrievalQuery, RetrievalService
from cats.retrieval.pgvector_store import PgVectorStore, _vector_literal
from cats.retrieval.testing import DeterministicHashEmbeddingProvider


class RecordingStore:
    def __init__(self):
        self.added = []
        self.last_search = None

    def add(self, document, vector):
        self.added.append((document, vector))

    def search(self, query_vector, *, top_k, financial_instrument_id=None):
        self.last_search = (query_vector, top_k, financial_instrument_id)
        return []


def test_retrieval_service_uses_vector_store_boundary_not_in_memory_type():
    store = RecordingStore()
    service = RetrievalService(DeterministicHashEmbeddingProvider(dimensions=8), store)
    document = EvidenceDocument(text="revenue growth", source_name="synthetic")
    instrument_id = uuid4()

    service.index([document])
    service.retrieve(
        RetrievalQuery(
            text="revenue growth",
            purpose="boundary test",
            financial_instrument_id=instrument_id,
            top_k=2,
        )
    )

    assert store.added[0][0] == document
    assert store.last_search[1:] == (2, instrument_id)


def test_pgvector_store_rejects_unsafe_table_name_without_connecting():
    with pytest.raises(ValueError, match="simple SQL identifier"):
        PgVectorStore(
            dsn="postgresql://unused",
            dimensions=3,
            table_name="bad-name;drop table x",
            ensure_schema=False,
        )


def test_pgvector_vector_literal_is_stable_and_requires_values():
    assert _vector_literal([1.0, 0.25, -2.0]) == "[1,0.25,-2]"
    with pytest.raises(ValueError, match="cannot be empty"):
        _vector_literal([])
