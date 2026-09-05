from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class EnvironmentCheck:
    name: str
    passed: bool
    detail: str


def inspect_environment(
    env: dict[str, str] | None = None,
    *,
    require_openai: bool = True,
) -> list[EnvironmentCheck]:
    env = dict(os.environ if env is None else env)
    checks: list[EnvironmentCheck] = []

    environment = env.get("CATS_ENVIRONMENT", "PAPER").upper()
    checks.append(EnvironmentCheck(
        "CATS environment",
        environment == "PAPER",
        f"CATS_ENVIRONMENT={environment}",
    ))

    db_url = env.get("CATS_DATABASE_URL", "")
    db_ok = db_url.startswith("postgresql+psycopg://") or db_url.startswith("postgresql://")
    checks.append(EnvironmentCheck(
        "PostgreSQL URL",
        db_ok,
        "Configured PostgreSQL URL" if db_ok else "CATS_DATABASE_URL is missing or not PostgreSQL",
    ))

    alpaca_key = env.get("ALPACA_API_KEY") or env.get("CATS_ALPACA_API_KEY")
    alpaca_secret = env.get("ALPACA_API_SECRET") or env.get("CATS_ALPACA_API_SECRET")
    checks.append(EnvironmentCheck(
        "Alpaca PAPER credentials",
        bool(alpaca_key and alpaca_secret),
        "Configured" if alpaca_key and alpaca_secret else "Missing Alpaca PAPER key/secret",
    ))

    openai_key = env.get("OPENAI_API_KEY")
    checks.append(EnvironmentCheck(
        "OpenAI API key",
        (not require_openai) or bool(openai_key),
        (
            "Configured"
            if openai_key
            else "Not required by selected runtime providers"
            if not require_openai
            else "Missing OPENAI_API_KEY"
        ),
    ))

    base_url = env.get("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    host = urlparse(base_url).hostname or ""
    paper_ok = host == "paper-api.alpaca.markets"
    checks.append(EnvironmentCheck(
        "Alpaca endpoint safety",
        paper_ok,
        base_url,
    ))

    return checks
