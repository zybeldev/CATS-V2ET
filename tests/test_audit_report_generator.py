from pathlib import Path


def test_audit_report_module_contains_json_and_markdown_writers():
    text = Path("src/cats/runtime/audit_report.py").read_text(encoding="utf-8")
    assert "def write_json" in text
    assert "def write_markdown" in text
    assert "PostRunVerifier" in text
