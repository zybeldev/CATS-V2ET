from types import SimpleNamespace

from cats.adapters.llm import OpenAIEmbeddingAdapter, OpenAIReasoningAdapter


class FakeResponses:
    def create(self, **kwargs):
        return SimpleNamespace(output_text='{"status":"PASS"}')


class FakeEmbeddings:
    def create(self, **kwargs):
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
        )


class FakeClient:
    responses = FakeResponses()
    embeddings = FakeEmbeddings()


def test_openai_reasoning_adapter_parses_json():
    adapter = OpenAIReasoningAdapter(api_key="x", model="test-model", client=FakeClient())
    assert adapter.reason_json(system_text="x", input_text="y") == {"status": "PASS"}


def test_openai_embedding_adapter_returns_vectors():
    adapter = OpenAIEmbeddingAdapter(api_key="x", client=FakeClient())
    assert adapter.embed(["hello"]) == [[0.1, 0.2, 0.3]]
