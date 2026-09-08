# CATS V2ET — Streamlit UI Step 21
## Auto PAPER Execution and Persistent Evaluation Control

### Purpose
Step 21 changes CATS from a monitoring loop with manual full-cycle activation into an operator-selectable runtime that can remain on and periodically initiate the existing full CATS PAPER authority chain.

This is **PAPER-only testing behavior**. It does not add a new trading authority and it does not force a trade.

### Operator modes
The dashboard now exposes a separate **Trading Activation** control:

- `MANUAL EVALUATION`
- `AUTO PAPER EXECUTION`

`AUTO PAPER EXECUTION` is available only while the system is stopped and `Operating Mode = PAPER EXECUTION`.

### AUTO PAPER EXECUTION behavior
When selected, the operator chooses an automatic full-evaluation cadence between 5 and 60 minutes; the default is 10 minutes.

The operator must explicitly check:

> I authorize CATS to initiate recurring Alpaca PAPER evaluations while the system is running, without another button press.

The authorization is passed only to the spawned CATS main-loop process. The loop refuses AUTO mode unless:

- `CATS_ENVIRONMENT=PAPER`;
- Qwen is configured;
- Alpaca PAPER credentials are available; and
- explicit recurring PAPER authorization is present.

### Trigger conditions
A full automatic evaluation is attempted only when:

1. the main loop is running in `AUTO_PAPER_EXECUTION`;
2. the configured cooldown has elapsed;
3. TAA has just produced a fresh `FINAL` monitoring assessment;
4. the selected V2ET instrument has a usable monitored news URL; and
5. no unresolved persisted PAPER flow blocks a new execution.

The automatic runner uses the same existing CATS PAPER launcher used by the operator UI. It does **not** bypass the authority chain:

`TAA -> PMA -> PMS when required -> SYS -> TEA -> TES -> Alpaca PAPER`

PMA remains responsible for Portfolio intent. SYS remains deterministic validation authority. TEA/TES retain execution responsibility. Therefore an automatic evaluation can legitimately produce **NO CHANGE / no order**.

### Outstanding-flow guard
Before starting a new automatic PAPER flow, Step 21 checks recent persisted flows. If any flow is still `STARTED`, `RUNNING`, `SUSPENDED`, `PENDING`, or `EXECUTING`, the automatic evaluation is skipped.

This preserves the existing CATS assurance rule: an outstanding execution must be recovered/reconciled using its original identity; CATS must not blindly create a replacement flow.

The dashboard status reports states such as:

- `COMPLETED`
- `FAILED`
- `TIMEOUT`
- `SKIPPED_NO_EVIDENCE`
- `SKIPPED_BLOCKING_FLOW`

### Persistent manual control
When CATS is running in PAPER EXECUTION with `MANUAL EVALUATION`, the sidebar now keeps a visible:

`RUN CATS EVALUATION NOW`

control. It uses the latest monitored Alpaca news URL as evidence and requires a one-run PAPER authorization checkbox.

The lower **Additional Evidence / Full Evaluation** section remains available for custom Website URL or Local File evidence.

When AUTO PAPER EXECUTION is active, manual run controls are disabled to prevent overlapping authority-chain flows.

### Chronology correction
Step 21 also corrects the main-loop TAA timestamp semantic identified during the Sep 4 behavior test:

- `Last TAA Assessment` now records assessment completion time rather than inference-start time.

This keeps main-loop chronology aligned with the persisted TAA assessment card.

### Runtime status additions
The Main Operating Loop now reports:

- `Activation`
- `Auto Evaluation Cadence`
- `Last Auto Evaluation`
- last automatic evaluation state

Operating Mode, Financial Instrument, and Trading Activation are locked while the loop is running. Stop CATS before changing them.

### Files
- `scripts/streamlit_dashboard.py`
- `scripts/cats_main_loop.py`
- `src/cats/runtime/main_loop.py`
- `tests/test_auto_paper_execution.py`

### Validation performed during patch construction
- Python compilation: PASS
- Main operating-loop + auto-execution focused tests: `9 passed`

The full user-environment regression suite must still be run after applying the patch.

### Apply
Stop the current CATS loop and Streamlit first.

```bash
cd ~/cats_v2et

unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_21_Auto_Paper_Execution.zip

unset CATS_EXECUTION_ACTIVATION
unset CATS_AUTO_PAPER_CONFIRM
unset CATS_AUTO_PAPER_SECONDS

python -m pytest -q
```

If the regression suite passes, run Streamlit with the aggressive PAPER test SYS profile if desired:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

### Start unattended PAPER testing
In the dashboard:

1. Select `PAPER EXECUTION`.
2. Select the financial instrument, for example `AAPL (Apple)`.
3. Select `AUTO PAPER EXECUTION`.
4. Leave cadence at `10` minutes for the initial one-hour test.
5. Check recurring Alpaca PAPER authorization.
6. Press `LOAD CATS SYSTEM`.

Expected Main Operating Loop status:

```text
System Operating Mode    PAPER EXECUTION
Activation               AUTO_PAPER_EXECUTION
Auto Evaluation Cadence  10 min
SYS Behavior Profile     AGGRESSIVE — PAPER TEST   # when enabled
```

No additional RUN button press is required while AUTO mode is running.

### Important test interpretation
AUTO mode makes full CATS evaluations autonomous. It does **not** manufacture BUY/SELL intent. Whether an Alpaca PAPER order is submitted still depends on the actual PMA decision and SYS validation.
