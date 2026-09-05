from datetime import datetime, timezone
from uuid import uuid4

import pytest

from cats.adapters.evidence import MCPPublicEvidenceSource, PublicEvidenceRequest
from cats.adapters.mcp import StdioMCPServerConfig, StdioMCPToolClient


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, dict(arguments)))
        return {
            "text": "Revenue increased while operating margin remained stable.",
            "source_name": arguments["source_name"],
            "external_reference": arguments["url"],
            "financial_instrument_id": arguments["financial_instrument_id"],
            "observed_at": arguments["observed_at"],
            "retrieved_at": "2026-08-30T12:00:00+00:00",
            "metadata": {"source_type": "PUBLIC_WEB"},
        }


def test_mcp_public_evidence_source_preserves_cats_evidence_contract():
    client = FakeMCPClient()
    source = MCPPublicEvidenceSource(client)
    instrument_id = uuid4()
    observed_at = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)

    document = source.ingest(
        PublicEvidenceRequest(
            url="https://example.test/results",
            source_name="Example Results",
            financial_instrument_id=instrument_id,
            observed_at=observed_at,
        )
    )

    assert client.calls[0][0] == "fetch_public_evidence"
    assert client.calls[0][1]["financial_instrument_id"] == str(instrument_id)
    assert document.financial_instrument_id == instrument_id
    assert document.observed_at == observed_at
    assert document.external_reference == "https://example.test/results"
    assert document.metadata["connector"] == "MCP"
    assert document.metadata["mcp_tool"] == "fetch_public_evidence"


def test_mcp_public_evidence_source_fails_on_empty_or_unstructured_result():
    class EmptyClient:
        def call_tool(self, name, arguments):
            return {"text": ""}

    with pytest.raises(ValueError, match="no usable text"):
        MCPPublicEvidenceSource(EmptyClient()).ingest(
            PublicEvidenceRequest(url="https://example.test", source_name="Example")
        )

    class BadClient:
        def call_tool(self, name, arguments):
            return "not structured"

    with pytest.raises(TypeError, match="structured mapping"):
        MCPPublicEvidenceSource(BadClient()).ingest(
            PublicEvidenceRequest(url="https://example.test", source_name="Example")
        )


def test_stdio_mcp_client_enforces_explicit_tool_allowlist_before_sdk_call():
    client = StdioMCPToolClient(
        StdioMCPServerConfig(command="python", args=("server.py",)),
        allowed_tools=frozenset({"fetch_public_evidence"}),
    )

    with pytest.raises(PermissionError, match="not authorized"):
        client.call_tool("submit_order", {"symbol": "AAPL"})
