from pathlib import Path


def test_operator_requires_explicit_paper_confirmation_for_run():
    text = Path("scripts/paper_operator.py").read_text(encoding="utf-8")
    assert "--confirm-paper" in text
    assert "Blocked: --confirm-paper is required." in text
