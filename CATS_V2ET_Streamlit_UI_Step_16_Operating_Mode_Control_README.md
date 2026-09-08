# CATS V2ET — Streamlit UI Step 16

## Operating Mode Control

This patch adds an explicit operator-facing CATS operating mode without changing the CATS architecture or authority model.

### Modes

- **EVALUATION / MONITORING** — default. Continuous TSS/TAA monitoring and historical-flow analysis remain available. Broker-order controls are locked in the UI.
- **PAPER EXECUTION** — exposes the existing `RUN CATS PAPER` full authority-chain control. The existing PAPER environment check, Qwen readiness check, SYS validation, and explicit operator confirmation remain required.

### UI changes

- Adds `Operating Mode` to the CATS System section.
- Adds current Operating Mode to the sidebar System card.
- Adds `System Operating Mode` to the Main Operating Loop card.
- Distinguishes `System Operating Mode` from the internal `Loop Mode` (`MONITORING`).
- In Evaluation mode, `Activation` reports `BLOCKED — EVALUATION MODE` and the PAPER execution form is not exposed.
- In PAPER Execution mode, the existing PAPER execution form becomes available.

### Safety / authority

This is an additional operator-interface gate. It does not redistribute authority:

`TAA → PMA → SYS → TEA → TES`

TSS remains a deterministic measurement service and PMS remains the deterministic optimization service when required.

### Validation

`python -m py_compile scripts/streamlit_dashboard.py` — PASS in the patch workspace.

A full project pytest suite was not run in the patch workspace and should be run after applying the patch to the user project.
