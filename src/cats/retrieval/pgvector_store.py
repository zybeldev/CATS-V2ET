from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from .models import EvidenceDocument, RetrievedEvidence

_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _vector_literal(values: list[float]) -> str:
    if not values:
        raise ValueError("Embedding vector cannot be empty")
    return "[" + ",".join(format(float(value), ".17g") for value in values) + "]"


class PgVectorStore:
    """PostgreSQL/pgvector implementation of the CATS vector-store boundary.

    This adapter changes storage/search technology only. Retrieval semantics,
    evidence objects, TAA responsibility, and authority boundaries are unchanged.
    """

    def __init__(
        self,
        *,
        dsn: str,
        dimensions: int,
        table_name: str = "cats_evidence_vectors",
        ensure_schema: bool = True,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if not _TABLE_NAME.fullmatch(table_name):
            raise ValueError("table_name must be a simple SQL identifier")

        self.dsn = dsn
        self.dimensions = dimensions
        self.table_name = table_name

        if ensure_schema:
            self.ensure_schema()

    def ensure_schema(self) -> None:
        from psycopg import connect

        with connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        evidence_document_id uuid PRIMARY KEY,
                        text text NOT NULL,
                        source_name text NOT NULL,
                        external_reference text,
                        financial_instrument_id uuid,
                        observed_at timestamptz,
                        retrieved_at timestamptz NOT NULL,
                        metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL
                    )
                    """
                )

    def add(self, document: EvidenceDocument, vector: list[float]) -> None:
        if len(vector) != self.dimensions:
            raise ValueError(
                f"Embedding dimension {len(vector)} does not match store dimension {self.dimensions}"
            )

        from psycopg import connect
        from psycopg.types.json import Jsonb

        with connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name} (
                        evidence_document_id,
                        text,
                        source_name,
                        external_reference,
                        financial_instrument_id,
                        observed_at,
                        retrieved_at,
                        metadata,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (evidence_document_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        source_name = EXCLUDED.source_name,
                        external_reference = EXCLUDED.external_reference,
                        financial_instrument_id = EXCLUDED.financial_instrument_id,
                        observed_at = EXCLUDED.observed_at,
                        retrieved_at = EXCLUDED.retrieved_at,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        document.evidence_document_id,
                        document.text,
                        document.source_name,
                        document.external_reference,
                        document.financial_instrument_id,
                        document.observed_at,
                        document.retrieved_at,
                        Jsonb(document.metadata),
                        _vector_literal(vector),
                    ),
                )

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        financial_instrument_id: UUID | None = None,
    ) -> list[RetrievedEvidence]:
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query dimension {len(query_vector)} does not match store dimension {self.dimensions}"
            )
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        vector = _vector_literal(query_vector)
        where_sql = ""
        params: list[Any] = [vector]
        if financial_instrument_id is not None:
            where_sql = "WHERE financial_instrument_id = %s"
            params.append(financial_instrument_id)
        params.extend([vector, top_k])

        from psycopg import connect

        with connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        evidence_document_id,
                        text,
                        source_name,
                        external_reference,
                        financial_instrument_id,
                        observed_at,
                        retrieved_at,
                        metadata,
                        1 - (embedding <=> %s::vector) AS cosine_similarity
                    FROM {self.table_name}
                    {where_sql}
                    ORDER BY embedding <=> %s::vector, evidence_document_id
                    LIMIT %s
                    """,
                    params,
                )
                rows = cursor.fetchall()

        results: list[RetrievedEvidence] = []
        for rank, row in enumerate(rows, start=1):
            (
                evidence_document_id,
                text,
                source_name,
                external_reference,
                instrument_id,
                observed_at,
                retrieved_at,
                metadata,
                score,
            ) = row
            document = EvidenceDocument(
                text=text,
                source_name=source_name,
                external_reference=external_reference,
                financial_instrument_id=instrument_id,
                observed_at=_as_datetime(observed_at),
                retrieved_at=_as_datetime(retrieved_at),
                metadata=dict(metadata or {}),
                evidence_document_id=evidence_document_id,
            )
            results.append(
                RetrievedEvidence(document=document, score=float(score), rank=rank)
            )
        return results


def _as_datetime(value: datetime | None) -> datetime | None:
    return value
