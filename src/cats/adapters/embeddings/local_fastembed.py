from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class LocalFastEmbedEmbeddingAdapter:
    """Local/open dense embedding provider using FastEmbed + ONNX Runtime.

    The production default is CPU-only. The model is loaded lazily on the first
    embedding call so importing CATS and running unit tests do not require the
    optional FastEmbed dependency or a network/model download.

    FastEmbed's CPU package uses ONNX Runtime and does not require PyTorch or
    CUDA. GPU acceleration, if ever justified, remains an implementation choice
    behind this same CATS embedding-provider boundary.
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    CPU_PROVIDER = "CPUExecutionProvider"

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
        model: Any | None = None,
    ):
        if not model_name:
            raise ValueError("model_name is required")
        self.model_name = model_name
        self.device = "cpu"
        self._model = model

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "Local embeddings require FastEmbed. Install the CPU-only dependency with "
                "`python -m pip install -r requirements-local-embeddings.txt`."
            ) from exc

        self._model = TextEmbedding(
            model_name=self.model_name,
            providers=[self.CPU_PROVIDER],
        )
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        items = list(texts)
        if not items:
            return []

        model = self._load_model()
        vectors = list(model.embed(items))
        result: list[list[float]] = []
        for row in vectors:
            values = row.tolist() if hasattr(row, "tolist") else list(row)
            result.append([float(value) for value in values])
        return result

    @property
    def embedding_dimension(self) -> int | None:
        """Return a model-provided dimension when exposed without forcing a probe."""
        model = self._load_model()
        for name in ("embedding_size", "dim", "dimension"):
            value = getattr(model, name, None)
            if value is None:
                continue
            value = value() if callable(value) else value
            if value is not None:
                return int(value)
        return None
