from __future__ import annotations

from collections.abc import Iterable

from .interfaces import EmbeddingProvider, VectorStore
from .models import EvidenceDocument, RetrievalQuery, RetrievedEvidence


class RetrievalService:
    """Demand-driven evidence retrieval for TAA.

    Retrieved text is evidence only. This service never converts retrieved
    content into CATS instructions, Portfolio Decisions, or execution actions.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, store: VectorStore):
        self.embedding_provider = embedding_provider
        self.store = store

    def index(self, documents: Iterable[EvidenceDocument]) -> None:
        docs = list(documents)
        if not docs:
            return
        vectors = self.embedding_provider.embed([d.text for d in docs])
        if len(vectors) != len(docs):
            raise ValueError("Embedding provider returned an unexpected vector count")
        for document, vector in zip(docs, vectors):
            self.store.add(document, vector)

    def retrieve(self, query: RetrievalQuery) -> list[RetrievedEvidence]:
        vector = self.embedding_provider.embed([query.text])[0]
        return self.store.search(
            vector,
            top_k=query.top_k,
            financial_instrument_id=query.financial_instrument_id,
        )
