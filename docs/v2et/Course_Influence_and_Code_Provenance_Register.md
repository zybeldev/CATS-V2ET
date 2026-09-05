# CATS V2ET — Course Influence and Code Provenance Register

**Status:** Living implementation record  
**Purpose:** Record where course material influenced V2ET code, how CATS adapted that influence, and where CATS implementation remains independent.

## Influence classifications

- **Conceptual Reference** — course material explains a mechanism; CATS implementation is independently designed.
- **Implementation Pattern** — course code provides a programming/algorithmic pattern that V2ET adapts.
- **Direct Adaptation** — a specific course code structure or algorithm is materially adapted.
- **Comparative Reference** — course implementation is inspected, but CATS intentionally implements the responsibility differently.
- **Independent CATS Design** — the mechanism predates or is independent of the course implementation.

## Register

| V2ET area | CATS code | Course/reference source | Influence | CATS adaptation | Status |
|---|---|---|---|---|---|
| TAA Tree-of-Thought reasoning | `src/cats/agents/taa/reasoning.py` | Module 4, Lab 1 — Tree of Thoughts; professor Module 4 material | Implementation Pattern + Independent CATS Design | Uses candidate generation, explicit evaluation/ranking, and bounded beam-style search. Branches are structured candidate financial assessments rather than Game-of-24 states. ToT remains inside TAA and returns the existing reasoning-model output expected by `Assessment`. | Implemented — Step 01 |
| TAA Reasoning Router | `src/cats/agents/taa/reasoning.py` | Module 4 ToT routing concept; prior CATS V1 TAA design | Conceptual Reference + Independent CATS Design | Direct and ToT strategies remain behind the existing `StructuredReasoningModel` boundary. Strategy selection does not alter TAA authority or contracts. | Implemented — Step 01 |
| RAG | existing `src/cats/retrieval/` | Module 3 RAG labs/slides | Comparative Reference + Independent CATS Design | V2E RAG predates V2ET. Course material is used to compare indexing, embeddings, retrieval, vector-store choices, and advanced retrieval techniques. | Existing baseline |
| pgvector | planned retrieval adapter | Module 3 vector-database concepts | Technology Evaluation | Compare persistent PostgreSQL/pgvector retrieval with the current in-memory vector store while preserving retrieval semantics. | Planned |
| Agent Harness | existing agent/runtime boundaries | Module 4 harness lab/slides | Comparative Reference + Independent CATS Design | CATS already separates authoritative state, evidence, tools, structured outputs, validation, and persistence. | Planned analysis |
| MCP public-evidence connector | `src/cats/adapters/mcp/`, `src/cats/adapters/evidence/mcp.py`, `scripts/mcp_public_evidence_server.py` | Module 1 MCP lab and professor MCP material | Implementation Pattern | Implements host/client/server tool-call pattern through a bounded read-only TAA evidence connector. Explicit tool allow-list prevents MCP discovery from granting CATS authority. TES remains on its direct broker API path because execution is latency-sensitive; MCP is not rejected for TES, but deferred pending future timing/reliability/control evaluation. | Implemented — Step 02 |
| LangGraph state/flow control | `src/cats/runtime/langgraph_orchestrator.py` | Module 5 workflow material; professor StateGraph examples; TA LangGraph/subagent reference | Implementation Pattern | Uses `StateGraph`, explicit edges, conditional routing, and compact control state. The graph starts at the existing TAA Assessment material boundary and coordinates PMA → SYS → TEA plus terminal control states. PMS and TES remain behind their existing PMA/TEA interfaces rather than being refactored merely for the framework. Domain logic, authority, and authoritative persistence remain in CATS. | Implemented — Step 03 |
| CrewAI | no implementation currently planned | Module 5 multi-agent material | Comparative Reference | Evaluate whether role/delegation abstractions solve a missing CATS problem. Current bounded system already has explicit roles, authority, and flow; framework overhead must be proportional to benefit. | Evaluation only |
| Open/local models | planned model adapters/evaluation | course local/open-model examples and Hugging Face references | Implementation Pattern | Preserve separate reasoning-model and embedding-model interfaces; OpenAI remains V2E reference implementation. | Planned |
| System Assurance / Operational Control | existing validation, TRACE, logging, recovery | Module 6 | Comparative Reference + Independent CATS Design | Compare course mechanisms with existing CATS controls; do not add an observability platform solely for the capstone. | Planned analysis |
| LangSmith | none in V2ET | course evaluation/observability references | Conceptual Reference | Deferred to full CATS V2 because V2ET does not require another observability platform at this scale. | Deferred to V2 |

## Step 01 — Tree-of-Thought notes

The course Lab 1 implementation separates thought generation, state evaluation, and bounded breadth-first/beam selection. V2ET preserves that mechanism at a higher semantic level:

```text
TAA evidence + measurements
        ↓
generate candidate assessments
        ↓
evaluate/rank candidates
        ↓
retain bounded frontier
        ↓
stress-test/refine retained candidates
        ↓
select highest-scoring candidate
        ↓
existing TAA Assessment boundary
```

The CATS implementation does **not** persist or expose hidden chain-of-thought text. Search nodes contain structured candidate assessments and compact evaluation metadata suitable for engineering evaluation.

## Step 02 — MCP notes

The course MCP implementation demonstrates standardized host/client/server communication and tool invocation. V2ET applies that pattern only to a latency-tolerant public-evidence capability.

```text
Course mechanism
MCP host/client/server + tools
        ↓
CATS adaptation
TAA public evidence connector
        ↓
existing EvidenceDocument / RAG / TAA boundaries
```

The decision not to place MCP on the TES broker path in V2ET is a technology-fit decision, not a categorical rejection of MCP. TES remains direct-API for the current implementation; future CATS V2 work may compare MCP with direct broker integration if equivalent timing, reliability, control, and failure behavior can be demonstrated.

## Step 03 — LangGraph notes

The course workflow examples demonstrate `StateGraph`, shared state, nodes, edges, conditional routing, and compilation into an executable workflow. V2ET applies that implementation pattern to the existing CATS runtime responsibility rather than adopting the course agent topology.

```text
Course mechanism
shared state + nodes + conditional edges
        ↓
CATS adaptation
TAA material boundary → PMA → SYS → TEA
        ↓
COMPLETED / SUSPENDED control states
```

The graph state contains identifiers and control indicators rather than full CATS business objects. PMS and TES remain behind their established PMA and TEA engineering interfaces. This is deliberate: framework topology does not redefine component interfaces simply to mirror every architecture box.
