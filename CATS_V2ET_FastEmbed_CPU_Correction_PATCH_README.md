# CATS V2ET — FastEmbed CPU Correction Patch

## Purpose

Correct the first local-embedding implementation so the default CATS embedding
runtime is genuinely lightweight and CPU-oriented.

The superseded patch used `sentence-transformers`, which caused pip to resolve
PyTorch and CUDA/NVIDIA packages. That dependency profile is unnecessary for
CATS embedding generation.

## New implementation

```text
CATS EmbeddingProvider
        ↓
LocalFastEmbedEmbeddingAdapter
        ↓
FastEmbed
        ↓
ONNX Runtime — CPUExecutionProvider
        ↓
local/open embedding model
```

Default model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

FastEmbed package:

```text
fastembed==0.8.0
```

No PyTorch, CUDA, or NVIDIA GPU package is required by this CATS local embedding
profile.

## Compatibility

The old `LocalSentenceTransformerEmbeddingAdapter` import remains as a
compatibility alias to the new FastEmbed implementation. It no longer imports
or depends on `sentence-transformers`.

OpenAI embeddings remain available only when explicitly selected with:

```text
--embedding-provider openai
```

## Operational rule

Document and query vectors in the same index must use the same embedding model.
When moving an existing persistent vector index from OpenAI embeddings to the
local 384-dimensional model, rebuild/re-embed that index rather than mixing
embedding spaces.

## Safe validation sequence

```bash
python -m pip install -r requirements-local-embeddings.txt
python -m pytest -q
python scripts/local_embedding_smoke_test.py
```

The smoke test performs embedding inference only. It has no broker/order side
effects.
