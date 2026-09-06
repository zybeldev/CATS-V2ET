# CATS V2ET — Software System Engineering Lessons Learned

**Version:** 0.2  
**Purpose:** Capture the principal Software System Engineering lessons learned through the development of CATS V1, CATS V2, CATS V2E, and CATS V2ET.

---

## 1. See the System Before Building the Parts

A Software System must first be understood and described as an integrated whole.

One of the simplest and most useful practical aids is a concise **System Description**: a human-readable explanation of what the system is, what purpose it serves, where its boundary lies, what environment it operates in, and how it interacts with that environment. The description is not itself a formal architecture step; it is a way for people to visualize and communicate the complete system before decomposition begins.

The high-level design must make visible:

- purpose;
- environment;
- system boundary;
- principal components;
- responsibilities;
- authority;
- relationships;
- information flows;
- state ownership;
- external actors.

Starting too quickly with local implementation questions can cause individual technologies, modules, or data structures to shape the system before the complete system is understood.

For complex systems, the high-level architecture serves the same purpose as a building blueprint: it allows the designer to see the whole plan before committing to detailed construction.

---

## 2. Do Not Begin Engineering Prematurely

CATS showed that moving too quickly from a partial architecture into engineering can create avoidable redesign cost.

Engineering, database structures, and software progressively become more expensive to change.

Architecture and early engineering design remain comparatively inexpensive to revise because they are still largely conceptual and documentary.

The lesson is not to delay engineering indefinitely. It is to wait until the system design is sufficiently mature that engineering is being directed by the system rather than defining it accidentally.

---

## 3. Define the Box and Its Boundary Interface Before Opening It

A useful architectural method emerged repeatedly during CATS design.

Before examining the internals of a component:

1. describe what the component is;
2. define its purpose;
3. define its boundary;
4. define its boundary interface;
5. define its inputs;
6. define its outputs;
7. define its responsibility;
8. define its authority;
9. define the state it owns or requires;
10. define its relationships.

Only then should the component be opened and decomposed internally.

This prevented internal implementation detail from obscuring the component's role in the larger system.

---

## 4. Progressive Decomposition Works Better Than Immediate Detail

The project became easier to reason about when the design moved progressively from:

```text
Reality / Environment
→ CATS as one integrated system
→ system boundary and inputs/outputs
→ principal architectural components
→ component responsibilities and authority
→ internal component mechanisms
```

The lesson is to lower the level of abstraction deliberately rather than jumping directly from a system idea into code, database tables, or framework structures.

---

## 5. Architect Forward to Preserve the Capability Horizon

CATS V2 required a broader architectural horizon than the bounded capstone implementation.

The architecture therefore planned for capabilities that V2ET did not fully implement, including broader Portfolio reasoning, execution reasoning, derivatives, multiple financial instruments, and future system extensions.

This was beneficial because future components, Agent roles, interfaces, authority boundaries, and data relationships could be considered before the implementation needed them.

The lesson is:

> Architect far enough ahead to preserve the system's foreseeable capability horizon.

Forward architecture should not become premature implementation.

---

## 6. Use a Bounded Vertical Slice to Ground the Design

A mature architecture should not remain theoretical indefinitely.

CATS benefited from implementing a narrow but complete vertical slice through the full authority and execution chain.

A vertical slice exposes the architecture to:

- engineering constraints;
- database and persistence requirements;
- runtime behavior;
- technology limitations;
- external systems;
- operational uncertainty;
- recovery requirements.

The vertical slice should be small enough to implement and evaluate, but complete enough to test whether the system works as a system.

The complementary principle is:

> Implement early enough and narrowly enough to expose the design to engineering and operational reality.

---

## 7. Engineering Is a Diagnostic Design Layer

Software Engineering Design does more than implement architecture.

It tests architecture.

During CATS development, lower-level analysis exposed:

- missing responsibilities;
- incomplete authority boundaries;
- state-ownership questions;
- reconciliation requirements;
- recovery requirements;
- execution semantics;
- persistence needs;
- external-system constraints.

These findings changed the higher-level design.

The lesson is:

> Do not descend so early that local engineering details dictate the architecture; do not remain so high that architectural assumptions escape engineering scrutiny.

---

## 8. Database / Persistence Design Should Follow Architectural and Engineering Scrutiny

Persistent structures are concrete commitments.

Once database tables, relationships, migrations, and application dependencies exist, structural change becomes more expensive. An early persistence model can harden incomplete assumptions into software and can stifle later capability expansion or broader system expansion.

CATS showed that persistence should be derived only after the selected vertical slice has been clarified at the System Design and Software Engineering Design levels.

The practical slice-level sequence is:

```text
Vertical Slice Software System Design
→ Bounded Vertical Slice
→ Software Engineering Design
→ Software System Database / Persistence Design
```

The database should realize the system's state model and relationships; it should not become the source from which the architecture is inferred.

---

## 9. Canonical Behavior Should Exist Before Optional Technology Complexity

CATS V2E established a technology-minimal canonical implementation before V2ET evaluated additional technologies.

This provided a stable behavioral reference.

The lesson is that the system's behavior and contracts should exist independently of optional frameworks, model providers, connector protocols, vector stores, or infrastructure choices.

Without a canonical reference, technology can silently become the source of system semantics.

---

## 10. Technology Should Remain Replaceable

CATS V2ET repeatedly demonstrated that implementation mechanisms could change while responsibilities remained stable.

Examples included:

- Qwen versus gpt-oss;
- transient retrieval versus pgvector-backed persistence;
- direct Python control flow versus LangGraph experiments;
- native adapters versus MCP-compatible connectivity;
- Colab versus RunPod infrastructure.

The system responsibility did not need to change simply because the implementation mechanism changed.

The lesson is:

> Interfaces define responsibilities and contracts; implementation details remain replaceable.

Technology implements the system; technology does not define it.

---

## 11. Agentic and Deterministic Responsibilities Should Be Deliberately Separated

The project reinforced the value of deciding where probabilistic reasoning is appropriate and where deterministic mechanisms should remain authoritative.

Probabilistic reasoning is valuable for interpretation, assessment, and ambiguous reasoning.

Deterministic mechanisms remain preferable for:

- exact calculations;
- policy enforcement;
- validation;
- state transitions;
- persistent identity;
- broker mechanics;
- recovery logic;
- invariants.

The system should not make a component agentic simply because an LLM is available.

---

## 12. State, Reality, and Reasoning Context Are Different Things

CATS exposed an important distinction between:

- persistent internal state;
- current external reality;
- reasoning context.

Persisted state may be stale.

External systems may have changed while CATS was offline.

Reasoning context is reconstructed information used for assessment and decision-making; it is not automatically authoritative state.

The lesson is that these concepts must remain separate in both architecture and implementation.

---

## 13. External Reality Must Be Reconciled, Not Assumed

Automated tests cannot fully validate behavior at an external system boundary.

CATS PAPER execution demonstrated that broker-confirmed reality must remain authoritative for external trading outcomes.

Uncertain API responses cannot be treated automatically as failure or success.

The system must preserve identity, query the external system, reconcile the outcome, and then update accepted internal state.

This became one of the strongest reliability lessons in V2ET.

---

## 14. Recovery Must Be Designed Before It Is Needed

Recovery is not an implementation afterthought.

CATS demonstrated that reliable recovery requires prior design of:

- stable execution identities;
- persistence;
- lineage;
- explicit uncertainty states;
- broker reconciliation;
- idempotency;
- startup recovery behavior.

Without those structures, an autonomous system may repeat consequential external actions after interruption.

---

## 15. Observability Is Not Authority

The Streamlit interface improved visibility, control, and technical review of CATS behavior.

But the interface did not become part of the financial decision authority chain.

The lesson is that operator interfaces should expose state and allow governed intervention without silently acquiring system authority.

---

## 16. Architecture Evolves Through Engineering Evidence

CATS V1, V2, V2E, and V2ET are best understood as accumulated design and engineering experience.

The progression was approximately:

```text
Initial Architecture
→ Engineering / Vertical Slice
→ Implementation Experience
→ Architectural Refinement
→ Revised Engineering
→ Technology Evaluation
→ Operational Validation
→ New Software System Design Knowledge
```

The project therefore demonstrated that architecture should neither be treated as permanently frozen nor casually changed.

It should evolve through controlled feedback from engineering and operational reality.

---

## 17. Software System Engineering Is an Iterative Learning Process

The development process itself exhibited the pattern of an adaptive system:

```text
Current Design
→ Action through Engineering
→ Observation through Testing and Operation
→ Evaluation
→ Feedback
→ Revised Design
```

Design artifacts therefore serve not only as documentation but also as accumulated engineering memory.

Lessons should be retained so that future projects do not repeat earlier design mistakes.

---

# Consolidated Lessons

The principal lessons from CATS V2ET are:

1. Understand and describe the complete system before building its parts.
2. Do not begin detailed engineering before Software System Design is sufficiently mature.
3. Define a component and its boundary interface before opening and decomposing it.
4. Lower the level of abstraction progressively.
5. Architect far enough ahead to preserve the foreseeable capability horizon.
6. Implement early enough and narrowly enough through a bounded vertical slice to ground the design in engineering and operational reality.
7. Use Software Engineering Design to test the architecture.
8. Derive persistence from Vertical Slice Software System Design and Software Engineering Design; do not let an early database constrain later system capability.
9. Establish canonical behavior before introducing optional technology complexity.
10. Preserve technology replaceability behind stable responsibilities and interfaces.
11. Separate probabilistic reasoning from deterministic authority deliberately.
12. Keep persistent state, external reality, and reasoning context distinct.
13. Reconcile external reality rather than assuming outcomes.
14. Design recovery, lineage, and idempotency before failures occur.
15. Keep observability and operator interfaces outside decision authority unless explicitly designed otherwise.
16. Allow architecture to evolve through controlled engineering evidence.
17. Preserve lessons as accumulated Software System Engineering experience.

---

# Relationship to the Software System Engineering Methodology

The **Software System Engineering Methodology** defines the general reusable engineering process.

This document records the CATS project experience that produced and strengthened many of those principles.

They are related, but they operate at different levels:

- **Methodology:** what to do when defining, designing, engineering, implementing, validating, and evolving a Software System.
- **Lessons Learned:** why those practices matter, based on what CATS V2ET exposed during actual architecture, engineering, implementation, persistence, testing, recovery, and operation.

The separate **Software System Engineering — Terminology, Professional Roles, and CATS Example** document defines the formal terminology and professional-role distinctions used by both documents.
