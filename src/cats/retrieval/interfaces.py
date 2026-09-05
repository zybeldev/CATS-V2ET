from __future__ import annotations

from typing import Protocol, Sequence
from uuid import UUID

from .models import EvidenceDocument, RetrievedEvidence


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class EvidenceSource(Protocol):
    def collect(self, query: str) -> list[EvidenceDocument]:
        ...


class VectorStore(Protocol):
    """Storage boundary for CATS semantic evidence retrieval."""

    def add(self, document: EvidenceDocument, vector: list[float]) -> None:
        ...

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        financial_instrument_id: UUID | None = None,
    ) -> list[RetrievedEvidence]:
        ...
