from scripts.external_run_preflight import STEPS


def test_external_preflight_contains_all_required_external_checks():
    names = [name for name, _ in STEPS]
    assert "Environment doctor" in names
    assert "PostgreSQL connectivity" in names
    assert "Database migrations" in names
    assert "Schema verification" in names
    assert "Alpaca PAPER smoke test" in names
    assert "Local CPU embedding smoke test" in names
    assert "OpenAI smoke test" not in names
