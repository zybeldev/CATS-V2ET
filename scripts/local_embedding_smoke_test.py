from __future__ import annotations

import argparse
import math
import time

from cats.adapters.embeddings import LocalFastEmbedEmbeddingAdapter


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load and smoke-test the local CPU embedding model. No broker/order action is performed."
    )
    parser.add_argument(
        "--model",
        default=LocalFastEmbedEmbeddingAdapter.DEFAULT_MODEL,
    )
    args = parser.parse_args()

    adapter = LocalFastEmbedEmbeddingAdapter(
        model_name=args.model,
    )

    texts = [
        "Apple reported stronger quarterly revenue growth.",
        "AAPL revenue increased in the latest quarter.",
        "Heavy rain affected regional crop production.",
    ]

    started = time.perf_counter()
    vectors = adapter.embed(texts)
    elapsed = time.perf_counter() - started

    if len(vectors) != len(texts):
        raise SystemExit("LOCAL EMBEDDING SMOKE: FAIL - vector count mismatch")
    dimensions = {len(v) for v in vectors}
    if len(dimensions) != 1 or next(iter(dimensions)) <= 0:
        raise SystemExit("LOCAL EMBEDDING SMOKE: FAIL - invalid embedding dimensions")

    related = cosine(vectors[0], vectors[1])
    unrelated = cosine(vectors[0], vectors[2])

    print("CATS V2ET LOCAL EMBEDDING SMOKE")
    print(f"Model: {adapter.model_name}")
    print(f"Device: {adapter.device}")
    print(f"Dimensions: {len(vectors[0])}")
    print(f"First load + embed seconds: {elapsed:.3f}")
    print(f"Related cosine similarity: {related:.6f}")
    print(f"Unrelated cosine similarity: {unrelated:.6f}")
    print("Broker/order side effects: NONE")
    print("LOCAL EMBEDDING SMOKE: PASS")


if __name__ == "__main__":
    main()
