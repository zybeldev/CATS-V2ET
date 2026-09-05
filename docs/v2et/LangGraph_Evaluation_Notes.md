# CATS V2ET — LangGraph Evaluation Notes

**Work Package:** 03  
**Status:** Bounded implementation complete; real LangGraph SDK validation pending in the user's WSL environment.

## Purpose

Evaluate LangGraph as the implementation technology for the existing CATS state-machine and principal-component flow-control responsibility without redefining CATS architecture or component authority.

## CATS principle

```text
CATS architecture
      ↓
principal component responsibilities
      ↓
state-machine / flow-control mechanism
      ↓
LangGraph implementation experiment
```

LangGraph is not the CATS architecture. It is one candidate runtime mechanism for controlling significant state transitions and the flow among CATS components.

## Course/reference influence

The Module 5 workflow material demonstrates the core LangGraph pattern:

```text
shared workflow state
      ↓
StateGraph
      ↓
nodes
      ↓
edges / conditional edges
      ↓
compiled executable workflow
```

The course lab progresses from a simple linear multi-agent workflow to conditional routing and iterative control. The TA LangGraph/subagent example is treated as an additional implementation reference.

CATS adapts the mechanism rather than copying the course topology.

## Implemented V2ET experiment

The bounded graph variation mirrors the existing `V2EOrchestrator.run_from_assessment()` slice:

```text
START
  ↓
TAA material boundary
  ↓
PMA
  ↓
SYS
  ├── FAIL / NO_CHANGE → COMPLETED
  └── PASS
         ↓
        TEA
         ├── verified → COMPLETED
         └── not verified → SUSPENDED
```

The graph starts from an already-produced TAA `Assessment`. The TAA node is therefore an ingress/material-boundary marker and does not invoke TAA reasoning a second time.

## Why PMS and TES are not separate nodes in this experiment

CATS V2E already exposes these current engineering call boundaries:

```text
PMA
  ↓
PMS optimizer service

TEA
  ↓
TES execution system
```

V2ET does not refactor those interfaces merely to make every architectural component appear as a graph node.

That would allow the framework to drive engineering structure rather than implement it.

Therefore:

- PMS remains invoked through PMA's existing optimizer boundary;
- TES remains invoked through TEA's existing execution boundary;
- internal component methods do not become graph nodes;
- future V2 engineering may expose additional principal-component transitions if justified independently of LangGraph.

## Graph state boundary

The LangGraph state intentionally carries only references and control indicators:

```text
flow_id
current_state
assessment_id
portfolio_decision_id
validation_result_id
execution_ids
completed
terminal_state
terminal_reason
path
```

Full CATS domain objects remain in the run context and are owned by the existing components.

This preserves the principle:

```text
LangGraph state
= workflow/control state

CATS contracts / persistence / TRACE
= material and authoritative state
```

## Technology isolation

LangGraph does not own:

- TAA reasoning;
- PMA Portfolio intent;
- PMS optimization;
- SYS rules;
- TEA execution reasoning;
- TES broker interaction;
- RAG;
- MCP;
- PostgreSQL persistence;
- TRACE;
- global system time.

It controls only the bounded workflow transitions demonstrated in this work package.

## Framework fit

LangGraph is narrower than a full role/delegation multi-agent framework for this CATS use case.

The value being tested is not "more agents." The value is explicit stateful flow control:

- visible transition structure;
- conditional routing;
- significant terminal states;
- future potential for waits, suspend/resume, recovery, and human intervention;
- separation of workflow state from component authority.

The framework must still justify its dependency and abstraction overhead relative to the pure-Python V2E baseline.

## Dependency policy

V2ET declares LangGraph as an optional dependency:

```text
langgraph>=1.2,<2
```

The upper major-version bound prevents an unreviewed future breaking API change from silently changing the experiment, following the dependency lesson learned during MCP Step 02A.

Install with:

```bash
pip install -e ".[dev,mcp,langgraph]"
```

or, when MCP is already installed:

```bash
pip install -e ".[dev,langgraph]"
```

## Validation

Construction-environment validation:

```text
66 passed, 1 skipped
```

The LangGraph-specific test module is skipped when the optional framework is not installed. The construction container has no external package-network access, so the real LangGraph SDK path must be validated in the user's WSL environment.

After installing the optional dependency, the expected full target is:

```text
69 passed
```

Then run:

```bash
python scripts/langgraph_backbone_smoke_test.py
```

Expected control result:

```text
LangGraph CATS backbone: PASS
path=TAA -> PMA -> SYS -> TEA -> COMPLETED
terminal_state=COMPLETED
terminal_reason=EXECUTION_VERIFIED
executions=1
```

This uses the deterministic CATS demo broker. It does not submit an Alpaca PAPER order.

## Evaluation questions

The next validation pass should record:

- Does the LangGraph variation preserve the same CATS authority semantics as the pure-Python baseline?
- Is the flow easier to inspect and reason about?
- Does conditional routing reduce custom orchestration code?
- What dependency and debugging overhead does the framework add?
- Is explicit graph state useful enough at the current project size to justify the framework?
- Which future CATS V2 waits, suspend/resume, recovery, or human-intervention paths would materially benefit from a state-machine mechanism?

## Feedforward candidate

The technology-neutral finding being tested is:

> CATS should provide an explicit state-machine mechanism at the principal-component level for significant system state and flow transitions when the operational complexity justifies it.

Whether that future mechanism is LangGraph remains an implementation decision.
