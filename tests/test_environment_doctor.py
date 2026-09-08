from cats.runtime.environment_doctor import inspect_environment
from cats.runtime.real_run import evaluate_real_run_gate


def valid_env():
    return {
        "CATS_ENVIRONMENT": "PAPER",
        "CATS_DATABASE_URL": "postgresql+psycopg://cats:cats@localhost:5432/cats_v2et",
        "ALPACA_API_KEY": "x",
        "ALPACA_API_SECRET": "y",
        "OPENAI_API_KEY": "z",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }


def test_environment_doctor_passes_valid_paper_configuration():
    checks = inspect_environment(valid_env())
    assert all(c.passed for c in checks)


def test_environment_doctor_blocks_live_alpaca_endpoint():
    env = valid_env()
    env["ALPACA_PAPER_BASE_URL"] = "https://api.alpaca.markets"
    checks = inspect_environment(env)
    endpoint = next(c for c in checks if c.name == "Alpaca endpoint safety")
    assert endpoint.passed is False


def test_real_run_gate_fails_when_credentials_missing():
    env = valid_env()
    env.pop("ALPACA_API_SECRET")
    gate = evaluate_real_run_gate(env)
    assert gate.ready is False
    assert "Alpaca PAPER credentials" in gate.failed_checks


def test_environment_doctor_allows_no_openai_when_runtime_does_not_require_it():
    env = valid_env()
    env.pop("OPENAI_API_KEY")
    checks = inspect_environment(env, require_openai=False)
    openai = next(c for c in checks if c.name == "OpenAI API key")
    assert openai.passed is True
    assert openai.detail == "Not required by selected runtime providers"
    gate = evaluate_real_run_gate(env, require_openai=False)
    assert gate.ready is True
