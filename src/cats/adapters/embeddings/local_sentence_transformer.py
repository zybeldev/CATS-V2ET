"""Compatibility shim for the superseded sentence-transformers adapter name.

CATS now uses FastEmbed + ONNX Runtime for the local CPU embedding implementation.
This module deliberately imports no sentence-transformers or PyTorch dependency.
"""

from .local_fastembed import LocalFastEmbedEmbeddingAdapter


# Preserve imports from the first local-embedding patch without preserving the
# heavyweight sentence-transformers implementation.
LocalSentenceTransformerEmbeddingAdapter = LocalFastEmbedEmbeddingAdapter

__all__ = ["LocalSentenceTransformerEmbeddingAdapter"]
