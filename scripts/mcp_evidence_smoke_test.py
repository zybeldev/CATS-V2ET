"""Smoke-test the V2ET MCP public-evidence connector over local stdio."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from cats.adapters.evidence import MCPPublicEvidenceSource, PublicEvidenceRequest
from cats.adapters.mcp import StdioMCPServerConfig, StdioMCPToolClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Public URL to retrieve through MCP")
    parser.add_argument("--source-name", default="V2ET MCP Smoke Test")
    args = parser.parse_args()

    server_script = Path(__file__).with_name("mcp_public_evidence_server.py").resolve()
    client = StdioMCPToolClient(
        StdioMCPServerConfig(
            command=sys.executable,
            args=(str(server_script),),
        ),
        allowed_tools=frozenset({MCPPublicEvidenceSource.TOOL_NAME}),
    )
    source = MCPPublicEvidenceSource(client)
    document = source.ingest(
        PublicEvidenceRequest(url=args.url, source_name=args.source_name)
    )
    print("MCP evidence connector: PASS")
    print(f"source={document.source_name}")
    print(f"reference={document.external_reference}")
    print(f"characters={len(document.text)}")
    print(f"connector={document.metadata.get('connector')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
