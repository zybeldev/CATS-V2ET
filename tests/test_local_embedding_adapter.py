from cats.adapters.embeddings import LocalFastEmbedEmbeddingAdapter
from cats.runtime.production_paper_flow import ProductionPaperFlow
from scripts.first_real_paper_flow import _build_embeddings


class FakeRow(list):
    def tolist(self):
        return list(self)


class FakeFastEmbedModel:
    embedding_size = 3

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return iter(FakeRow([1.0, 0.0, 0.5]) for _ in texts)


def test_local_embedding_adapter_uses_fastembed_boundary_and_cpu_contract():
    model = FakeFastEmbedModel()
    adapter = LocalFastEmbedEmbeddingAdapter(model=model)

    vectors = adapter.embed(["alpha", "beta"])

    assert vectors == [[1.0, 0.0, 0.5], [1.0, 0.0, 0.5]]
    assert adapter.device == "cpu"
    assert adapter.embedding_dimension == 3
    assert model.calls == [["alpha", "beta"]]


def test_local_embedding_adapter_empty_batch_does_not_load_model():
    adapter = LocalFastEmbedEmbeddingAdapter(model=None)
    assert adapter.embed([]) == []


def test_paper_launcher_defaults_can_build_local_embeddings_without_openai_key():
    adapter = _build_embeddings(provider="local", model_name=None, openai_key=None)
    assert isinstance(adapter, LocalFastEmbedEmbeddingAdapter)
    assert adapter.device == "cpu"


def test_production_flow_defaults_to_local_embeddings_when_reasoning_is_injected():
    flow = ProductionPaperFlow(
        alpaca_api_key="x",
        alpaca_api_secret="y",
        reasoning=object(),
        broker=object(),
        market_data=object(),
        evidence_source=object(),
    )
    assert flow.reasoning is not None
    assert isinstance(flow.embeddings, LocalFastEmbedEmbeddingAdapter)
    assert flow.embeddings.device == "cpu"
