# CATS V2ET — Implementation Log

## Branch baseline

- Source: uploaded `cats_v2e.zip`
- Baseline test result in clean extracted tree: **60 passed**
- Architecture: unchanged
- Authority model: unchanged

## Step 01 — TAA Tree-of-Thought reasoning

Implemented:

- bounded `TreeOfThoughtAssessmentModel`;
- structured candidate assessment nodes;
- explicit candidate evaluation/ranking;
- beam-width and depth budgets;
- `TAAReasoningRouter` for Direct vs Tree-of-Thought strategy selection;
- compact ToT run metrics for later comparison;
- deterministic tests;
- Course Influence and Code Provenance Register.

CATS boundaries preserved:

- ToT remains internal to TAA reasoning;
- TAA cannot create Portfolio intent;
- no Portfolio, SYS, TEA, TES, persistence, or runtime contracts were changed;
- the existing `StructuredReasoningModel` boundary is preserved;
- no hidden chain-of-thought transcript is persisted.

## Step 02 — MCP public-evidence connector

Implemented:

- narrow `MCPToolClient` boundary;
- optional official-SDK `StdioMCPToolClient`;
- explicit MCP tool allow-list;
- `MCPPublicEvidenceSource` preserving the existing `EvidenceDocument` contract;
- read-only `fetch_public_evidence` FastMCP server;
- stdio MCP smoke-test script;
- MCP technology-fit and TES latency decision documentation;
- deterministic tests for evidence-contract preservation and authorization.

CATS boundaries preserved:

- MCP is attached only to a latency-tolerant external evidence capability in this work package;
- TAA remains informational only;
- existing RAG and Assessment contracts are unchanged;
- TES remains on the direct Alpaca broker API path;
- MCP capability discovery does not grant authority;
- no broker execution, Portfolio intent, SYS validation, or persistence responsibility moved into MCP.

Validation:

- Step 01 baseline: **63 tests passed**.
- Step 02 code baseline: **66 tests passed**.
- Official MCP SDK smoke test initially remained pending in the construction environment because the optional `mcp` package was unavailable there.

Next planned work package after MCP smoke validation: LangGraph principal-component state/flow control.

## Step 02A — MCP SDK compatibility correction

Observed during the first real WSL MCP stdio smoke test:

- the MCP client package was installed successfully;
- the stdio child server terminated during initialization;
- the server-side `mcp.server.fastmcp.FastMCP` import failed under the newly resolved MCP major version;
- the client consequently reported `MCPError: Connection closed`.

Correction:

- constrain the optional MCP dependency to `mcp>=1.28,<2`, the v1.x maintenance line compatible with the implemented FastMCP API;
- improve the server startup error so a future SDK/API mismatch reports the underlying import failure rather than a misleading "not installed" message.

Engineering lesson:

> Optional framework dependencies must be version-bounded when the implementation depends on a major-version-specific API. A passing unit suite does not validate an optional external SDK that is absent from the test environment.

CATS architecture and authority boundaries are unchanged.

## Step 02B — MCP real SDK validation

Validated in the user's WSL V2ET environment after Step 02A:

```text
66 passed
MCP evidence connector: PASS
source=MCP Public Evidence Smoke Test
reference=https://example.com
characters=142
connector=MCP
```

This completed the real MCP client → stdio server → tool → public evidence path. TES remained unchanged on the direct Alpaca API path.

## Step 03 — LangGraph principal-component state/flow control

Implemented:

- optional `langgraph>=1.2,<2` dependency group;
- compact `CATSBackboneState` carrying identifiers/control indicators only;
- `LangGraphV2ETOrchestrator` as a technology variation of the existing V2E vertical-slice coordinator;
- TAA material-boundary ingress node;
- PMA and SYS component-flow nodes;
- conditional SYS routing;
- TEA execution node using the existing TEA/TES boundary;
- explicit COMPLETED and SUSPENDED control states;
- deterministic LangGraph tests for verified execution, SYS rejection, and NO_CHANGE routing;
- local LangGraph smoke-test script;
- LangGraph evaluation notes and provenance update.

CATS boundaries preserved:

- LangGraph does not become the CATS architecture;
- PMA remains Portfolio-intent authority;
- SYS remains deterministic validation authority;
- TEA remains execution-state authority;
- PMS remains invoked through PMA's existing optimizer interface;
- TES remains invoked through TEA's existing execution interface;
- no internal component methods were promoted into graph nodes;
- graph state contains references/control indicators rather than authoritative domain payloads;
- RAG, MCP, PostgreSQL, and TRACE are not moved under LangGraph.

Construction-container validation:

```text
66 passed, 1 skipped
```

The only skipped module is the LangGraph-specific test module because the optional framework is not installed and the construction container cannot reach external package repositories. After installation in WSL, the Step 03 target is **69 passed**, followed by `scripts/langgraph_backbone_smoke_test.py`.

Engineering lesson:

> A workflow framework should expose and control significant transitions already present in the system; it should not force existing domain services or authority boundaries to be decomposed merely to match the framework's graph representation.
