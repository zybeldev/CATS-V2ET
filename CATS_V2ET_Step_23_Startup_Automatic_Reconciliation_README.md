# CATS V2ET — Step 23
## Automatic Startup Reconciliation

### Purpose

Step 23 implements the already-defined CATS restart/recovery behavior in the V2ET operating runtime.

Before normal TSS/TAA monitoring or PAPER evaluation begins, CATS checks PostgreSQL for non-terminal `PRODUCTION_PAPER` flows. Existing `ACTIVE` or `SUSPENDED` flows are reconciled against Alpaca PAPER using their persisted execution/order identity.

No new execution intent is created and no replacement broker order is submitted during startup recovery.

### Startup behavior

```text
LOAD CATS SYSTEM
    ↓
normal external preflight
    ↓
start CATS main-loop process
    ↓
scan persisted PRODUCTION_PAPER flows
    ↓
ACTIVE / SUSPENDED flow found?
    ↓ yes
recover the EXISTING flow
    ↓
query Alpaca by persisted client_order_id
    ↓
reconcile broker-confirmed order/fill reality
    ↓
persist reconciled execution state and broker facts
    ↓
create verified ExecutionResult when complete
    ↓
PMA persists broker-confirmed accepted Portfolio State
    ↓
mark original TRACE_Flow COMPLETED
    ↓
start normal CATS operating loop
```

If recovery cannot establish a safe resolved state, startup fails closed:

```text
Startup Recovery = BLOCKED
Main Loop does not begin normal autonomous operation
```

### Operator UI

The System sidebar and Main Operating Loop card now show `Startup Recovery`:

- `CLEAR` — no non-terminal PAPER flow required recovery;
- `COMPLETED · N flow(s)` — startup recovered N existing flows;
- `BLOCKED · N unresolved` — normal operation is prevented until recovery is resolved.

### Sep 4 test case

The current Sep 4 AAPL flow is an ideal recovery test:

- one CATS flow;
- one TEA execution;
- one TEA `SUBMIT` action, attempt 1;
- one TES market order for about `47.214630626` AAPL;
- initial Alpaca response `NEW` / confirmed;
- initial CATS reconciliation at filled quantity `0`;
- Alpaca later filled the same order in three fills;
- CATS was stopped during patching before the next reconciliation;
- persisted flow remained `SUSPENDED`.

After this patch, loading CATS should recover that same persisted order. It must not submit another AAPL order.

### Files

- `scripts/cats_main_loop.py`
- `scripts/streamlit_dashboard.py`
- `src/cats/runtime/main_loop.py`
- `src/cats/runtime/startup_recovery.py`
- `tests/test_startup_paper_recovery.py`

### Validation during patch construction

Focused recovery validation:

```text
5 passed
```

Python compilation of the changed runtime/UI files: PASS.

The full regression suite must still be run in the user's current V2ET environment after applying the patch.

### Apply

Stop CATS and Streamlit first.

```bash
cd ~/cats_v2et

unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Step_23_Startup_Automatic_Reconciliation.zip

unset CATS_SYS_PROFILE
unset CATS_EXECUTION_ACTIVATION
unset CATS_AUTO_PAPER_CONFIRM
unset CATS_AUTO_PAPER_SECONDS

python -m pytest -q
```

If the full regression passes, start the PAPER test runtime as usual:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

Select `PAPER EXECUTION`, authorize the PAPER session, and press `LOAD CATS SYSTEM`.

Expected startup result for the Sep 4 suspended flow:

```text
Startup Recovery  COMPLETED · 1 flow(s)
Main Loop         RUNNING
```

Then confirm the original flow is now `COMPLETED` and verify it:

```bash
python scripts/verify_flow.py --flow-id 17e7c671-1972-455e-9590-e4c438b3ead9
```
