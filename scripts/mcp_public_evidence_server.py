"""Local MCP server exposing one bounded CATS public-evidence capability.

This server is intentionally read-only and latency-tolerant. It does not expose
TES broker execution or any capability that can create financial intent.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cats.adapters.evidence.public import PublicEvidenceRequest, PublicWebEvidenceSource

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - optional runtime dependency
    raise SystemExit(
        'V2ET MCP server requires the MCP Python SDK v1.x FastMCP API. '
        'Install the project MCP extra with: pip install -e ".[mcp]". '
        f'Import error: {exc}'
    ) from exc


mcp = FastMCP("cats-v2et-public-evidence")
source = PublicWebEvidenceSource()


@mcp.tool()
def fetch_public_evidence(
    url: str,
    source_name: str,
    financial_instrument_id: str | None = None,
    observed_at: str | None = None,
) -> dict:
    """Fetch public web evidence and return normalized, read-only evidence data."""
    document = source.ingest(
        PublicEvidenceRequest(
            url=url,
            source_name=source_name,
            financial_instrument_id=(
                None if financial_instrument_id is None else UUID(financial_instrument_id)
            ),
            observed_at=None if observed_at is None else datetime.fromisoformat(observed_at),
        )
    )
    return {
        "text": document.text,
        "source_name": document.source_name,
        "external_reference": document.external_reference,
        "financial_instrument_id": (
            None
            if document.financial_instrument_id is None
            else str(document.financial_instrument_id)
        ),
        "observed_at": (
            None if document.observed_at is None else document.observed_at.isoformat()
        ),
        "retrieved_at": document.retrieved_at.isoformat(),
        "metadata": {
            **document.metadata,
            "connector": "MCP",
            "mcp_server": "cats-v2et-public-evidence",
        },
    }


if __name__ == "__main__":
    mcp.run()
