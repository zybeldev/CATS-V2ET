from .local_fastembed import LocalFastEmbedEmbeddingAdapter
from .local_sentence_transformer import LocalSentenceTransformerEmbeddingAdapter

# Compatibility export: OpenAI embeddings remain available for explicit
# comparison/fallback, but are no longer the CATS default.
from cats.adapters.llm.openai_adapter import OpenAIEmbeddingAdapter

__all__ = [
    "LocalFastEmbedEmbeddingAdapter",
    "LocalSentenceTransformerEmbeddingAdapter",
    "OpenAIEmbeddingAdapter",
]
