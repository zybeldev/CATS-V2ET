from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from cats.ui.execution_entry import (
    build_paper_command,
    normalize_symbol,
    stage_local_evidence,
    validate_evidence_reference,
)


def test_normalize_symbol_accepts_plain_ticker_and_uppercases():
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol("brk.b") == "BRK.B"


def test_normalize_symbol_rejects_shell_like_input():
    with pytest.raises(ValueError):
        normalize_symbol("AAPL; rm -rf /")


def test_validate_evidence_reference_accepts_https_and_rejects_other_schemes():
    assert validate_evidence_reference("https://example.com/aapl") == "https://example.com/aapl"
    with pytest.raises(ValueError):
        validate_evidence_reference("javascript:alert(1)")


def test_stage_local_text_evidence_creates_stable_file_reference(tmp_path: Path):
    staged = stage_local_evidence(
        project_root=tmp_path,
        filename="Apple note.txt",
        data=b"Apple public evidence text.",
    )
    assert staged.original_path.is_file()
    assert staged.evidence_path.is_file()
    assert staged.evidence_reference.startswith("file://")
    assert "Apple public evidence text." in staged.evidence_path.read_text(encoding="utf-8")
    assert validate_evidence_reference(staged.evidence_reference) == staged.evidence_reference


def test_stage_local_docx_extracts_document_text(tmp_path: Path):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            "<w:body><w:p><w:r><w:t>Apple local DOCX evidence</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )
    staged = stage_local_evidence(
        project_root=tmp_path,
        filename="apple.docx",
        data=buffer.getvalue(),
    )
    assert "Apple local DOCX evidence" in staged.evidence_path.read_text(encoding="utf-8")


def test_build_paper_command_uses_argument_list_and_explicit_paper_confirmation(tmp_path: Path):
    evidence = tmp_path / "evidence.html"
    evidence.write_text("hello", encoding="utf-8")
    command = build_paper_command(
        project_root=tmp_path,
        symbol="aapl",
        evidence_reference=evidence.resolve().as_uri(),
        qwen_endpoint_url="https://example.trycloudflare.com/reason",
    )
    assert command[0]
    assert command[1].endswith("scripts/first_real_paper_flow.py")
    assert command[command.index("--symbol") + 1] == "AAPL"
    assert "--confirm-paper" in command
    assert command[command.index("--qwen-endpoint-url") + 1] == "https://example.trycloudflare.com/reason"
