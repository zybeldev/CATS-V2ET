from __future__ import annotations

import argparse
from uuid import uuid4

import psycopg
from psycopg import sql

from cats.retrieval import (
    EvidenceDocument,
    InMemoryVectorStore,
    PgVectorStore,
    RetrievalQuery,
    RetrievalService,
)
from cats.retrieval.testing import DeterministicHashEmbeddingProvider


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare CATS in-memory retrieval with pgvector using identical evidence and embeddings."
    )
    parser.add_argument(
        "--dsn",
        default="postgresql://postgres:cats@localhost:55432/cats_v2et_pgvector",
    )
    parser.add_argument("--table-name", default="v2et_cats_retrieval_eval")
    args = parser.parse_args()

    dimensions = 32
    embedder = DeterministicHashEmbeddingProvider(dimensions=dimensions)
    instrument_id = uuid4()
    other_instrument_id = uuid4()

    documents = [
        EvidenceDocument(
            text="revenue growth accelerated this quarter",
            source_name="synthetic-positive",
            external_reference="evidence-1",
            financial_instrument_id=instrument_id,
        ),
        EvidenceDocument(
            text="revenue growth slowed this quarter",
            source_name="synthetic-mixed",
            external_reference="evidence-2",
            financial_instrument_id=instrument_id,
        ),
        EvidenceDocument(
            text="weather conditions affected crop production",
            source_name="synthetic-unrelated",
            external_reference="evidence-3",
            financial_instrument_id=instrument_id,
        ),
        EvidenceDocument(
            text="revenue growth accelerated this quarter",
            source_name="other-instrument",
            external_reference="evidence-4",
            financial_instrument_id=other_instrument_id,
        ),
    ]

    query = RetrievalQuery(
        text="revenue growth accelerated this quarter",
        purpose="V2ET pgvector retrieval comparison",
        financial_instrument_id=instrument_id,
        top_k=3,
    )

    memory = RetrievalService(embedder, InMemoryVectorStore())
    memory.index(documents)
    memory_results = memory.retrieve(query)

    with psycopg.connect(args.dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(args.table_name))
            )

    pg_store = PgVectorStore(
        dsn=args.dsn,
        dimensions=dimensions,
        table_name=args.table_name,
    )
    pg_service = RetrievalService(embedder, pg_store)
    pg_service.index(documents)
    pg_results = pg_service.retrieve(query)

    # Recreate only the Python store/service object. The database rows must remain.
    persisted_service = RetrievalService(
        embedder,
        PgVectorStore(
            dsn=args.dsn,
            dimensions=dimensions,
            table_name=args.table_name,
        ),
    )
    persisted_results = persisted_service.retrieve(query)

    memory_ids = [item.document.evidence_document_id for item in memory_results]
    pg_ids = [item.document.evidence_document_id for item in pg_results]
    persisted_ids = [item.document.evidence_document_id for item in persisted_results]

    print("CATS V2ET STEP 06C — PGVECTOR RETRIEVAL EVALUATION")
    print("=" * 72)
    print("\nIn-memory ranking:")
    for item in memory_results:
        print(f"  {item.rank}. {item.document.external_reference} score={item.score:.6f}")

    print("\npgvector ranking:")
    for item in pg_results:
        print(f"  {item.rank}. {item.document.external_reference} score={item.score:.6f}")

    ranking_match = memory_ids == pg_ids
    persistence_match = pg_ids == persisted_ids
    instrument_filter_pass = all(
        item.document.financial_instrument_id == instrument_id for item in pg_results
    )

    print("\nChecks:")
    print("  ranking_matches_in_memory:", ranking_match)
    print("  survives_new_store_instance:", persistence_match)
    print("  instrument_filter_preserved:", instrument_filter_pass)

    passed = ranking_match and persistence_match and instrument_filter_pass
    print("\nSTEP 06C RESULT:", "PASS" if passed else "FAIL")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
