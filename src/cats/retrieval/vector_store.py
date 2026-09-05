from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from uuid import UUID

from .models import EvidenceDocument, RetrievedEvidence


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding dimensions do not match")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class _StoredVector:
    document: EvidenceDocument
    vector: list[float]


class InMemoryVectorStore:
    """Simple vector store for tests and the first capstone vertical slice.

    The interface can later be replaced by pgvector or another external vector
    store without changing TAA authority or retrieval semantics.
    """

    def __init__(self) -> None:
        self._items: list[_StoredVector] = []

    def add(self, document: EvidenceDocument, vector: list[float]) -> None:
        self._items.append(_StoredVector(document=document, vector=vector))

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        financial_instrument_id: UUID | None = None,
    ) -> list[RetrievedEvidence]:
        scored: list[tuple[float, EvidenceDocument]] = []
        for item in self._items:
            if (
                financial_instrument_id is not None
                and item.document.financial_instrument_id != financial_instrument_id
            ):
                continue
            score = cosine_similarity(query_vector, item.vector)
            scored.append((score, item.document))

        scored.sort(key=lambda x: (-x[0], str(x[1].evidence_document_id)))
        return [
            RetrievedEvidence(document=doc, score=score, rank=index + 1)
            for index, (score, doc) in enumerate(scored[:top_k])
        ]
