from pathlib import Path


def test_run_and_audit_requires_explicit_paper_confirmation():
    text = Path("scripts/run_paper_and_audit.py").read_text(encoding="utf-8")
    assert "--confirm-paper" in text
    assert "Blocked: --confirm-paper is required." in text
    assert "generate_audit_report.py" in text
