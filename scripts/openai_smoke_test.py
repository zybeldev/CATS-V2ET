import os

from cats.adapters.llm import OpenAIEmbeddingAdapter, OpenAIReasoningAdapter


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("SKIP: OPENAI_API_KEY is not configured.")

    embedding = OpenAIEmbeddingAdapter(api_key=api_key)
    vector = embedding.embed(["CATS V2E smoke test"])[0]

    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise SystemExit("SKIP: OPENAI_MODEL is not configured.")
    reasoning = OpenAIReasoningAdapter(api_key=api_key, model=model)
    result = reasoning.reason_json(
        system_text="Return JSON only.",
        input_text='Return exactly {"status":"PASS"} as JSON.',
    )

    print("OpenAI authentication/API: PASS")
    print(f"Embedding dimensions: {len(vector)}")
    print(f"Reasoning result: {result}")


if __name__ == "__main__":
    main()
