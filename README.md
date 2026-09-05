# CATS V2ET

## Capstone Autonomous Trading System — V2 Technology Evaluation

CATS V2ET is the technology-evaluation implementation of the Capstone Autonomous Trading System developed for the CMU Executive Education Agentic AI Program.

CATS V2 is designed to autonomously construct, manage, optimize, and adapt an investment Portfolio while pursuing investor objectives within defined risk, capital, and governance constraints.

V2ET implements a bounded equity-only vertical slice of that architecture using public, synthetic, and PAPER-trading resources.

## Architecture

CATS separates financial interpretation, Portfolio authority, deterministic optimization, validation, execution responsibility, quantitative measurement, and broker-facing mechanisms.

Technology implements the system; technology does not define the architecture.

Financial Reality / Evidence
          |
          v
         TSS
          |
          v
         TAA
          |
          v
         PMA <----> PMS
          |
          v
         SYS
          |
          v
         TEA
          |
          v
         TES
          |
          v
      Alpaca PAPER

Primary components:

- TAA — Trading Assessment Agent: LLM-backed financial interpretation and assessment
- TSS — Trading Signal Service: deterministic market, technical, and statistical measurements
- PMA — Portfolio Management Agent: Portfolio intent and Portfolio State authority
- PMS — Portfolio Management Service: deterministic Portfolio optimization
- SYS — deterministic validation and operating authority
- TEA — Trading Execution Agent: execution responsibility within the authorized Portfolio target
- TES — broker-facing execution mechanisms
- DAS — Derivatives Analysis Service; part of broader CATS V2 and deferred from V2ET

## Agentic AI and Technology Evaluation

V2ET implements and evaluates technologies within defined CATS responsibilities while preserving architectural authority boundaries.

- Qwen3-14B-AWQ — selected reference TAA reasoning model
- gpt-oss-20b — comparative TAA reasoning implementation
- Tree of Thoughts — implemented and evaluated using bounded dynamic beam search within TAA
- MCP — external connector mechanism evaluation
- LangGraph — workflow/state-machine evaluation
- FastEmbed + ONNX — local embedding generation and transient semantic retrieval
- pgvector — validated optional persistent semantic retrieval
- PostgreSQL — durable state, lineage, and execution persistence
- Alpaca PAPER — broker integration and external execution validation
- Streamlit — operator and observability interface

### Tree of Thoughts

The TAA Tree-of-Thought implementation uses dynamically generated reasoning candidates with bounded beam search:

Current State
     |
     v
Thought Generator
generate k candidates
     |
     v
Evaluator
     |
     v
Beam Search
retain best <= b states
     |
     v
Expand Survivors
     |
     v
Repeat until T or termination

Where:

- k = generation branching factor
- b = beam width
- T = maximum reasoning depth

## Retrieval

The current V2ET retrieval path uses FastEmbed with ONNX to generate local CPU embeddings for demand-driven semantic retrieval into TAA reasoning context.

For persistent evidence retrieval, CATS supports PostgreSQL with pgvector so evidence and embeddings can be retained and searched across sessions.

## Safety and Authority

V2ET operates only against Alpaca PAPER.

Probabilistic reasoning does not directly perform external side effects. Financial interpretation, Portfolio decisions, validation, execution responsibility, and broker interaction remain separated by explicit component contracts and authority boundaries.

Execution uncertainty is handled through persisted identities and broker reconciliation rather than blind order resubmission.

## Persistence and Recovery

CATS persists Portfolio State, Execution State, lineage, broker identifiers, and operational history in PostgreSQL.

Startup recovery can identify incomplete broker-facing transactions, compare persisted CATS records with broker-confirmed data, reconcile the external outcome, and restore consistent internal state.

## Validation

The final regression suite completed with:

154 passed

The implementation includes tests covering:

- deterministic calculations
- component contracts
- authority boundaries
- persistence
- recovery
- integration
- Tree-of-Thought behavior
- TAA reasoning
- SYS validation
- TEA execution
- TSS measurements
- UI behavior

External validation also included:

- fresh PostgreSQL database and migrations
- Alpaca PAPER connectivity
- PAPER order execution
- broker fill reconciliation
- Portfolio State reconciliation
- persisted execution lineage
- startup recovery of an incomplete execution flow

## Repository Structure

src/          CATS V2ET implementation
tests/        automated regression tests
scripts/      evaluation, validation, runtime, and recovery utilities
migrations/   PostgreSQL migrations
docs/         engineering and technology-evaluation documentation

## Setup

Create a Python environment:

python -m venv .venv
source .venv/bin/activate

Install the project and supporting dependencies:

pip install -e .
pip install -r requirements-local-embeddings.txt
pip install -r requirements-ui.txt

Use the supplied environment example files to create your own local configuration.

Never commit .env files or credentials.

PostgreSQL configuration is provided through docker-compose.yml.

## Tests

Run the regression suite with:

unset CATS_SYS_PROFILE
python -m pytest -q

## Scope

CATS V2ET is a capstone technology-evaluation implementation and not a production trading system.

Current scope is intentionally limited to:

- equities
- Alpaca PAPER
- PAPER capital
- one selected instrument per evaluation cycle
- one broker integration

Derivatives, broader asset classes, multiple brokers, production deployment, and live-capital trading remain outside the V2ET scope.

## Author

Cesar Muñoz Fournier

Developed through human-AI engineering collaboration with OpenAI.

## Academic Context

CMU Executive Education
Agentic AI Program
Final Capstone Project — 2026
