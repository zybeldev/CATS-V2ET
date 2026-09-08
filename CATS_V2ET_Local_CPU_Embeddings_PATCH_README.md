# CATS V2ET — Local CPU Embeddings Patch

## Purpose

Replace the default OpenAI embedding dependency with a local/open embedding model while preserving the existing CATS `EmbeddingProvider` boundary.

Default implementation:

```text
sentence-transformers/all-MiniLM-L6-v2
Device: CPU
```

The reasoning-model path is unchanged. Qwen remains the reference reasoning model when injected through the existing reasoning interface.

## What Changed

- Added `cats.adapters.embeddings` as the embedding-specific adapter namespace.
- Added `LocalSentenceTransformerEmbeddingAdapter`.
- Local embeddings are lazy-loaded and default to CPU.
- `ProductionPaperFlow` now defaults to local embeddings when no embedding adapter is explicitly injected.
- `first_real_paper_flow.py` now defaults to `--embedding-provider local`.
- OpenAI embeddings remain available as an explicit comparison/fallback implementation.
- A Qwen + local-embedding PAPER runtime no longer requires an OpenAI API key merely for embeddings.
- Environment/real-run gating can now mark OpenAI as not required when the selected runtime providers do not use it.
- Added a read-only local embedding smoke test. It performs no broker or order action.

## Important Embedding-Space Rule

A vector index must not mix embeddings created by different models. If a persistent pgvector corpus is later switched from OpenAI embeddings to this local model, re-embed the stored document chunks and use the same local model for query embeddings.

The current `ProductionPaperFlow` still uses its existing retrieval-store wiring; this patch changes the embedding implementation only.

## Install

From `~/cats_v2et` after unzipping the patch:

```bash
python -m pip install -r requirements-local-embeddings.txt
```

The first local model use may download and cache the open model. Do this during off hours as planned.

## Validate Code

```bash
python -m pytest -q
```

## Load/Cache and Smoke-Test the Local Embedding Model

This command is read-only with respect to trading and does not submit any broker order:

```bash
python scripts/local_embedding_smoke_test.py
```

It prints the model, CPU device, embedding dimensions, timing, and two cosine-similarity examples.

## PAPER Launcher Behavior

Default:

```text
embedding provider = local
embedding model    = sentence-transformers/all-MiniLM-L6-v2
device             = cpu
```

Optional comparison/fallback:

```bash
--embedding-provider openai
```

Optional local model override:

```bash
--embedding-model <model-name>
```

## Known Remaining Legacy Path

The uploaded patch-input archive did not include `scripts/external_run_preflight.py`. The existing full-project preflight therefore still contains its historical OpenAI smoke step until that script is updated separately. Do not delete the existing OpenAI environment configuration solely on the basis of this patch yet.
