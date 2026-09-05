# CATS V2ET — MCP Evaluation Notes

**Work Package:** 02  
**Status:** Bounded implementation complete; real MCP SDK/client/server smoke validation passed in the user's WSL environment after the Step 02A compatibility correction.

## Purpose

Evaluate Model Context Protocol (MCP) as a standardized connector mechanism for CATS external capabilities without changing CATS architecture, authority, or component responsibilities.

## Technology-fit principle

MCP is a candidate where interoperability and standardization provide value and the capability is not operationally time- or latency-sensitive.

MCP is **not rejected** for critical paths. For V2ET, however, direct purpose-built integration remains the default for latency-sensitive mechanisms unless MCP can later demonstrate equivalent timing, reliability, control, and failure behavior.

## V2ET decision

```text
Latency-tolerant external capability
        ↓
MCP candidate
        ↓
TAA public evidence experiment

Latency-sensitive execution capability
        ↓
TES
        ↓
direct Alpaca broker API in V2ET
```

TES remains on the direct broker API path for V2ET. A future CATS V2 evaluation may compare direct broker integration with MCP if the protocol/runtime can meet the execution path's timing, reliability, control, and recovery requirements.

## Implemented experiment

The first MCP experiment exposes one read-only public-evidence tool:

```text
TAA / runtime
    ↓
MCPPublicEvidenceSource
    ↓
MCPToolClient
    ↓
MCP stdio session
    ↓
fetch_public_evidence
    ↓
public web source
    ↓
EvidenceDocument
    ↓
existing V2E RAG pipeline
```

The existing CATS `EvidenceDocument`, retrieval service, TAA contract, and authority boundaries are unchanged.

## Authority control

The CATS-facing MCP client supports an explicit tool allow-list. Capability discovery does not grant CATS authority. The TAA evidence connector is authorized only for the read-only `fetch_public_evidence` capability.

No MCP server or tool is introduced into TES, broker order submission, Portfolio intent, SYS validation, or other financially consequential authority paths in this work package.

## Course influence

The course MCP material contributed the implementation pattern:

- host/client/server separation;
- standardized tool exposure;
- initialization/capability negotiation;
- tool invocation over MCP;
- explicit capability boundaries.

CATS determines where that mechanism belongs and constrains its authority.

## Current validation

- V2ET Step 01 baseline: **63 tests passed**.
- V2ET Step 02 after MCP connector implementation: **66 tests passed**.
- Unit tests validate CATS evidence-contract preservation, structured MCP result handling, failure behavior, and explicit tool authorization.
- The first WSL stdio smoke test exposed a major-version API mismatch when the unbounded dependency resolved to MCP 2.x. The project now pins `mcp>=1.28,<2` for the implemented v1.x FastMCP API.
- After that correction, the real MCP stdio client/server smoke test passed against `https://example.com`, returning a CATS `EvidenceDocument` with `connector=MCP`.

## External smoke test

Install the optional MCP dependency using the project-pinned compatible SDK line:

```bash
pip install -e ".[dev,mcp]"
```

For Step 02, `pyproject.toml` constrains MCP to `mcp>=1.28,<2` because the implementation uses the v1.x FastMCP server API.

Then run against a public URL:

```bash
python scripts/mcp_evidence_smoke_test.py \
  --url "https://example.com" \
  --source-name "MCP Public Evidence Smoke Test"
```

This validates the actual MCP SDK/client/server path. It does not modify TES or submit any broker order.

## Evaluation questions for the next validation pass

- Does the MCP connector preserve the same evidence semantics as the direct adapter?
- What integration code moves from the CATS side to the MCP server side?
- Does MCP materially improve connector standardization and capability discovery?
- What runtime and debugging overhead is introduced?
- What are the timing characteristics for this latency-tolerant evidence use case?
- Is a persistent MCP session preferable to the initial one-session-per-call prototype?

The initial stdio implementation opens a fresh MCP session for each call for simplicity. Its timing must not be treated as a general measurement of MCP protocol latency; persistent-session performance requires separate evaluation.
