from __future__ import annotations

import argparse
import os

from cats.adapters.embeddings import (
    LocalFastEmbedEmbeddingAdapter,
    OpenAIEmbeddingAdapter,
)
from cats.adapters.llm import RemoteQwenReasoningAdapter
from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.runtime.production_paper_flow import ProductionPaperFlow, ProductionPaperFlowInput
from cats.runtime.real_run import require_real_run_ready


def _build_embeddings(*, provider: str, model_name: str | None, openai_key: str | None):
    if provider == "local":
        return LocalFastEmbedEmbeddingAdapter(
            model_name=model_name or LocalFastEmbedEmbeddingAdapter.DEFAULT_MODEL,
        )
    if provider == "openai":
        if not openai_key:
            raise SystemExit("Blocked: OPENAI_API_KEY is required for OpenAI embeddings.")
        return OpenAIEmbeddingAdapter(
            api_key=openai_key,
            model=model_name or os.getenv("CATS_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    raise SystemExit(f"Blocked: unsupported embedding provider: {provider}")


def main():
    parser = argparse.ArgumentParser(
        description="Run the complete persistent CATS V2ET Alpaca PAPER authority chain."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--evidence-url", action="append", required=True)
    parser.add_argument("--confirm-paper", action="store_true")
    parser.add_argument(
        "--qwen-endpoint-url",
        help="Optional remote Qwen /reason endpoint. If omitted, OpenAI reasoning is used.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=("local", "openai"),
        default=os.getenv("CATS_EMBEDDING_PROVIDER", "local"),
        help="Embedding implementation. Default: local CPU FastEmbed/ONNX Runtime.",
    )
    parser.add_argument(
        "--embedding-model",
        default=os.getenv("CATS_EMBEDDING_MODEL"),
        help=(
            "Embedding model override. Local default: "
            f"{LocalFastEmbedEmbeddingAdapter.DEFAULT_MODEL}."
        ),
    )
    args = parser.parse_args()

    if not args.confirm_paper:
        raise SystemExit("Blocked: --confirm-paper is required.")

    openai_required = (not args.qwen_endpoint_url) or args.embedding_provider == "openai"
    require_real_run_ready(require_openai=openai_required)
    settings = get_settings()

    alpaca_key = os.getenv("ALPACA_API_KEY") or os.getenv("CATS_ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_API_SECRET") or os.getenv("CATS_ALPACA_API_SECRET")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL")

    reasoning = None
    if args.qwen_endpoint_url:
        qwen_token = os.getenv("CATS_QWEN_SESSION_TOKEN")
        if not qwen_token:
            raise SystemExit(
                "Blocked: CATS_QWEN_SESSION_TOKEN must be configured for remote Qwen."
            )
        reasoning = RemoteQwenReasoningAdapter(
            endpoint_url=args.qwen_endpoint_url,
            session_token=qwen_token,
        )
    elif not openai_model:
        raise SystemExit("Blocked: OPENAI_MODEL is required when OpenAI reasoning is selected.")

    embeddings = _build_embeddings(
        provider=args.embedding_provider,
        model_name=args.embedding_model,
        openai_key=openai_key,
    )

    engine = create_engine_from_settings(settings)
    Session = create_session_factory(engine)

    with Session() as session:
        flow = ProductionPaperFlow(
            alpaca_api_key=alpaca_key,
            alpaca_api_secret=alpaca_secret,
            openai_api_key=openai_key,
            openai_model=openai_model,
            session=session,
            reasoning=reasoning,
            embeddings=embeddings,
        )
        try:
            result = flow.run(
                ProductionPaperFlowInput(
                    symbol=args.symbol,
                    evidence_urls=tuple(args.evidence_url),
                    openai_model=openai_model,
                )
            )
        except Exception:
            if flow.last_visibility_report is not None:
                print("\nPARTIAL CATS FLOW VISIBILITY\n")
                print(flow.last_visibility_report.render_text())
            raise

        if result.visibility_report is not None:
            print("\n" + result.visibility_report.render_text())

        print("\nMATERIAL RESULT IDS")
        print("-" * 78)
        print(result)


if __name__ == "__main__":
    main()
