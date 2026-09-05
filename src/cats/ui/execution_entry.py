from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from zipfile import ZipFile
from io import BytesIO
from xml.etree import ElementTree as ET


_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_LOCAL_FILE_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".docx"}


@dataclass(frozen=True)
class StagedEvidence:
    original_filename: str
    original_path: Path
    evidence_path: Path
    evidence_reference: str
    sha256_hex: str


def normalize_symbol(value: str) -> str:
    symbol = (value or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError(
            "Financial instrument must be a simple ticker symbol such as AAPL, BRK.B, or RDS-A."
        )
    return symbol


def validate_evidence_reference(value: str) -> str:
    reference = (value or "").strip()
    if not reference:
        raise ValueError("Evidence source is required.")

    parsed = urlparse(reference)
    if parsed.scheme in {"http", "https"}:
        if not parsed.netloc:
            raise ValueError("Website evidence must include a valid host name.")
        return reference

    if parsed.scheme == "file":
        path = Path(parsed.path)
        if not path.is_file():
            raise ValueError("The staged local evidence file does not exist.")
        return reference

    raise ValueError("Evidence must be an http(s) website or a staged local file.")


def build_paper_command(
    *,
    project_root: Path,
    symbol: str,
    evidence_reference: str,
    qwen_endpoint_url: str | None,
) -> list[str]:
    clean_symbol = normalize_symbol(symbol)
    clean_reference = validate_evidence_reference(evidence_reference)

    launcher = project_root / "scripts" / "first_real_paper_flow.py"
    command = [
        sys.executable,
        str(launcher),
        "--symbol",
        clean_symbol,
        "--evidence-url",
        clean_reference,
        "--confirm-paper",
    ]
    if qwen_endpoint_url:
        command.extend(["--qwen-endpoint-url", qwen_endpoint_url.strip()])
    return command


def _safe_filename(filename: str) -> str:
    name = Path(filename or "evidence.txt").name
    safe = _SAFE_NAME_RE.sub("_", name).strip("._")
    return safe or "evidence.txt"


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _docx_text(data: bytes) -> str:
    with ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    chunks: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            chunks.append(node.text)
        elif node.tag.endswith("}p") and chunks:
            chunks.append("\n")
    return " ".join("".join(chunks).split())


def stage_local_evidence(
    *,
    project_root: Path,
    filename: str,
    data: bytes,
) -> StagedEvidence:
    safe_name = _safe_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _LOCAL_FILE_EXTENSIONS:
        allowed = ", ".join(sorted(_LOCAL_FILE_EXTENSIONS))
        raise ValueError(f"Unsupported local evidence file type. Supported: {allowed}.")
    if not data:
        raise ValueError("The uploaded evidence file is empty.")

    digest = sha256(data).hexdigest()
    target_dir = project_root / ".cats_ui_evidence" / digest[:16]
    target_dir.mkdir(parents=True, exist_ok=True)

    original_path = target_dir / f"original_{safe_name}"
    original_path.write_bytes(data)

    if suffix in {".html", ".htm"}:
        evidence_path = target_dir / safe_name
        evidence_path.write_bytes(data)
    else:
        if suffix == ".docx":
            text = _docx_text(data)
        else:
            text = _decode_text(data)
        if not text.strip():
            raise ValueError("The local evidence file contains no usable text.")
        evidence_path = target_dir / f"{Path(safe_name).stem}.html"
        evidence_path.write_text(
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            f"<title>{escape(safe_name)}</title>"
            f"<meta name=\"cats-original-filename\" content=\"{escape(safe_name)}\">"
            f"<meta name=\"cats-content-sha256\" content=\"{digest}\">"
            "</head><body>"
            f"<h1>{escape(safe_name)}</h1>"
            f"<p>CATS local evidence file. SHA-256: {digest}</p>"
            f"<pre>{escape(text)}</pre>"
            "</body></html>",
            encoding="utf-8",
        )

    return StagedEvidence(
        original_filename=safe_name,
        original_path=original_path,
        evidence_path=evidence_path,
        evidence_reference=evidence_path.resolve().as_uri(),
        sha256_hex=digest,
    )
