# CATS V2ET — Software System Engineering Lessons Learned

**Version:** 0.2  
**Purpose:** Capture the principal Software System Engineering lessons learned through the development of CATS V1, CATS V2, CATS V2E, and CATS V2ET.

CATS evolved through several project stages rather than emerging as a finished design. CATS V1 established the first coherent Software System Architecture and provided the first descent into Software Engineering Design. The lessons learned from that stage clarified component interaction, system flows, responsibilities, authority, and future expansion needs. Those findings informed CATS V2, which introduced a broader and more flexible Architecture. CATS V2E and V2ET then continued the cycle through canonical implementation, technological implementation, testing, validation, and operational feedback.

The lessons in this document were therefore learned progressively across these project stages and reflect the accumulated Software System Engineering experience of CATS.

---

# Engineering Cycles Followed

The lessons in this document emerged while CATS moved through two related engineering views: the practical Software System Design cycle used to turn architecture into working software, and the broader Software System Engineering cycle that governs the system from definition through mature operation.

## Software System Design Cycle

```text
Software System Design
→ Software System Architecture Design
→ Software Engineering Design
→ Software System Database / Persistence Design
→ Canonical Implementation
→ Technological Implementation
→ Testing / Validation
→ Feedback into Software System Design
```

This shorter cycle captures the repeated design-to-implementation path used during CATS engineering. Feedback from implementation and validation returned to System Design when the evidence showed that the design required refinement.

## Full Software System Engineering Cycle

```text
Software System Definition
→ Software System Architecture Design
→ Progressive Architectural Decomposition
→ Architectural Forward Planning
→ Sufficient Software System Design Maturity
→ Frozen Software System Architecture
→ Vertical Slice Software System Design
→ Bounded Vertical Slice
→ Software Engineering Design
→ Software System Database / Persistence Design
→ Canonical Implementation
→ Technological Implementation
→ Testing / Validation
→ Feedback into Software System Design
→ Next Vertical Slice / Iteration
→ Mature Operation / Maintenance
```

The full cycle places the practical implementation loop inside the larger lifecycle of defining, maturing, freezing, implementing, validating, operating, and maintaining the Software System.

During this process, CATS produced a series of practical lessons that progressively improved how the Software System was understood, designed, engineered, implemented, and validated. Those lessons are captured below.

---

## 1. Envision the System Before Building the Parts

Before decomposing a Software System into components, the designer should first form a coherent mental picture of the system as an integrated whole.

One practical aid is a **System Description**: a human-readable explanation of what the system is, what purpose it serves, where its boundary lies, what environment it operates in, and how it interacts with that environment.

The objective is not to produce a finished Architecture at this stage. It is to establish enough understanding of the whole system to begin architectural design without allowing individual components, technologies, databases, or implementation details to define the system prematurely.

The initial view should make visible:

- purpose;
- environment;
- system boundary;
- principal inputs and outputs;
- major external actors;
- principal components as they become identifiable;
- major responsibilities and relationships;
- major information and control flows.

As the project progresses, this mental picture becomes clearer through Architecture, Engineering Design, implementation, testing, and feedback.

---

## 2. Define the Box and Its Boundary Interface Before Opening It

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

Only then should the component be opened and decomposed internally into subcomponents. Each subcomponent should then be treated as a new box and defined through the same boundary-interface methodology before its own internal decomposition.

Repeating this process progressively lowers the level of abstraction while preserving the relationship of each component to the Software System as a whole. Progressive decomposition is therefore a direct consequence of the box methodology rather than a separate design principle.

This prevented internal implementation detail from obscuring the component's role in the larger system.

---

## 3. Design the Current System Without Closing Future Expansion

Software System Design should satisfy the requirements of the system being implemented now, but it should not unnecessarily restrict foreseeable future expansion.

The Architecture should provide enough structural flexibility for later requirements to introduce:

- new capabilities;
- new components or Agents;
- new interfaces;
- broader data relationships;
- additional external systems;
- new operating modes;
- greater scale.

This becomes especially important when the design reaches **Software System Database / Persistence Design**. Persistence structures are more concrete and costly to change than architectural models. If the Architecture is too narrowly defined, the database may encode assumptions that later constrain new capabilities. Expanding the system can then require expensive schema changes, migrations, data transformation, and software rework. It may also require substantial reconciliation among the revised Database / Persistence Design, the Software Engineering Design, and the Software System Architecture so that state ownership, interfaces, relationships, and system behavior remain consistent.

The objective is not to implement future capabilities prematurely. It is to avoid structural decisions that make reasonable future expansion unnecessarily difficult.

CATS V2 emerged from limitations discovered in CATS V1. V1 established the first coherent system structure, but the first descent into Engineering Design revealed where that structure was too narrow for future expansion. V2 incorporated those lessons through a broader and more flexible Architecture.

In CATS V2, architectural flexibility allowed options, foreign exchange, and other future capabilities to be incorporated without changing the principal system structure.

The lesson is:

> Design the current Software System with enough structural flexibility that foreseeable future capabilities can be added without forcing major reconciliation among Architecture, Engineering Design, and Persistence Design.

---

## 4. Evaluate Technology Against the System, Not the System Against the Technology

One of the recurring challenges during the CATS capstone was that the course was organized around technology. Individual modules introduced technologies and techniques such as **MCP, RAG, vector databases, agent frameworks, reasoning strategies, and observability tools**.

There was a natural temptation to modify the CATS Architecture each time a new technology was introduced so that the project could demonstrate that technology, and this became a recurring tension throughout the capstone.

Instead, CATS continued to develop primarily from its **Software System Architecture and Canonical Implementation**. New technologies were not allowed to redefine component responsibilities, authority, state ownership, interfaces, or system behavior merely because they appeared in a course module.

The sequence remained:

```text
Software System Architecture
→ Software Engineering Design
→ Canonical Implementation
→ establish expected system behavior
→ evaluate technology
→ attach technology where it provides a legitimate implementation mechanism
→ validate whether it improves or supports the system
```

This approach eventually proved valuable. Once the Canonical Implementation was sufficiently stable, technologies could be evaluated at clearly defined attachment points. Some could be incorporated, some could remain optional, and some could be rejected without changing the principal CATS structure.

In CATS V2ET, the purpose of the technology-evaluation implementation therefore became to determine how technologies could realize or improve established system responsibilities rather than allowing those technologies to determine what CATS should be.

The lesson is:

> Define and stabilize the Software System before evaluating technologies against it. Technology should satisfy the Architecture; the Architecture should not be redesigned merely to accommodate a technology.

---

## 5. Do Not Begin Engineering Prematurely

CATS showed that moving too quickly from a partial architecture into engineering can create avoidable redesign cost.

Engineering, database structures, and software progressively become more expensive to change.

Architecture and early engineering design remain comparatively inexpensive to revise because they are still largely conceptual and documentary.

The lesson is not to delay engineering indefinitely. It is to wait until the Software System Architecture is sufficiently mature that Engineering Design is being directed by the Architecture rather than defining it accidentally.

---

## 6. Engineering Is a Diagnostic Design Layer

Software System Architecture and Software Engineering Design observe the same Software System from different levels of abstraction.

At the **Software System Architecture** level, the designer maintains the higher-altitude, bird's-eye view required to see the Software System as an integrated whole: its principal components, responsibilities, authority, relationships, interfaces, state ownership, invariants, and major flows.

Once the Architecture is sufficiently mature, selected parts of the system can descend into **Software Engineering Design**. Engineering remains a relatively high-level design activity, but it operates at a lower altitude. From this closer view, details become visible that cannot always be seen clearly from the architectural level.

In CATS V1, the first descent into Engineering Design clarified how the principal components would actually interact and made the system flows more explicit. That closer view improved understanding of the Software System itself and produced early feedback into the Architecture.

During CATS development, the engineering view also exposed:

- missing or ambiguous responsibilities;
- incomplete authority boundaries;
- state-ownership questions;
- component interaction details;
- sequencing and flow requirements;
- persistence needs;
- reconciliation requirements;
- recovery behavior;
- execution semantics;
- external-system constraints.

The relationship is:

```text
Software System Architecture
→ sufficient architectural maturity
→ descend into Software Engineering Design
→ discover interactions, flows, states, interfaces, and constraints
→ feedback into Software System Architecture
→ refine or confirm the Architecture
→ continue Engineering Design
```

The lesson is:

> Different levels of abstraction provide different fields of vision. Engineering Design provides an early, closer view of the system that reveals details capable of refining the Software System Architecture.

---

## 7. Use a Bounded Vertical Slice to Ground the Design

A mature architecture should not remain theoretical indefinitely.

CATS benefited from implementing a narrow but complete vertical slice through the full authority and execution chain.

A vertical slice exposes the design to:

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

## 8. Agentic and Deterministic Responsibilities Should Be Deliberately Separated

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

## 9. State, Reality, and Reasoning Context Are Different Things

CATS exposed an important distinction between:

- persistent internal state;
- current external reality;
- reasoning context.

Persisted state may be stale.

External systems may have changed while CATS was offline.

Reasoning context is reconstructed information used for assessment and decision-making; it is not automatically authoritative state.

The lesson is that these concepts must remain separate in both architecture and implementation.

---

## 10. Database / Persistence Design Should Follow Architectural and Engineering Scrutiny

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

## 11. Canonical Behavior Should Exist Before Optional Technology Complexity

CATS V2E established a technology-minimal canonical implementation before V2ET evaluated additional technologies.

This provided a stable behavioral reference.

The lesson is that the system's behavior and contracts should exist independently of optional frameworks, model providers, connector protocols, vector stores, or infrastructure choices.

Without a canonical reference, technology can silently become the source of system semantics.

---

## 12. Technology Should Remain Replaceable

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
→ Engineering Design
→ early architectural feedback
→ refined Architecture
→ bounded implementation
→ implementation experience
→ technology evaluation
→ operational validation
→ new Software System Design knowledge
```

The project therefore demonstrated that Architecture should neither be treated as permanently frozen nor casually changed.

It should evolve through controlled feedback from Engineering Design, implementation, testing, and operational reality.

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

The principal lessons from CATS V2ET, ordered along the Software System Engineering progression, are:

1. Envision the complete Software System before building its parts.
2. Define each box and its boundary interface before opening it; apply the same method progressively to its subcomponents.
3. Design the current Software System with enough structural flexibility to preserve foreseeable future expansion.
4. Evaluate technologies against the established Software System rather than allowing technologies to drive the Architecture.
5. Do not descend into Engineering Design until the Software System Architecture is sufficiently mature to direct it.
6. Use Engineering Design as an early diagnostic layer: a lower-altitude view that reveals component interactions, flows, states, interfaces, and constraints that can refine the Architecture.
7. Use a bounded vertical slice to expose the design to engineering and operational reality.
8. Separate probabilistic reasoning from deterministic authority deliberately.
9. Keep persistent state, external reality, and reasoning context distinct.
10. Derive persistence from mature System Design and Engineering Design; do not let an early database constrain later system capability.
11. Establish canonical behavior before introducing optional technology complexity.
12. Preserve technology replaceability behind stable responsibilities and interfaces.
13. Reconcile external reality rather than assuming outcomes.
14. Design recovery, lineage, and idempotency before failures occur.
15. Keep observability and operator interfaces outside decision authority unless explicitly designed otherwise.
16. Allow Architecture to evolve through controlled evidence from Engineering Design, implementation, testing, and operation.
17. Preserve lessons as accumulated Software System Engineering experience.

---

# Relationship to the Software System Engineering Methodology

The **Software System Engineering Methodology** defines the general reusable engineering process.

This document records the CATS project experience that produced and strengthened many of those principles.

They are related, but they operate at different levels:

- **Methodology:** what to do when defining, designing, engineering, implementing, validating, and evolving a Software System.
- **Lessons Learned:** why those practices matter, based on what CATS V2ET exposed during actual architecture, engineering, implementation, persistence, testing, recovery, and operation.

The separate **Software System Engineering — Terminology, Professional Roles, and CATS Example** document defines the formal terminology and professional-role distinctions used by both documents.
