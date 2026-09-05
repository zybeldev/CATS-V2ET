from types import SimpleNamespace

from cats.adapters.llm import OpenAIReasoningAdapter


class FakeResponses:
    def create(self, **kwargs):
        return SimpleNamespace(output_text='{"summary":"grounded","confidence":0.8}')


class FakeClient:
    responses = FakeResponses()


def test_openai_adapter_implements_taa_reason_interface():
    adapter = OpenAIReasoningAdapter(api_key="x", model="test-model", client=FakeClient())
    result = adapter.reason(task="assess", context={"retrieved_evidence": []})
    assert result["summary"] == "grounded"
    assert result["confidence"] == 0.8
