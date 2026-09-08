# CATS V2ET — Streamlit UI Step 22
## Two-Mode Operation and Latest-Flow Selection

### Purpose
Stabilize the operator interface around the two CATS operating modes agreed for V2ET:

1. `EVALUATION / MONITORING`
2. `PAPER EXECUTION`

No third operator-facing activation mode is exposed.

### Operator behavior

#### EVALUATION / MONITORING
- TSS market surveillance continues.
- TAA monitoring assessments continue.
- Broker execution is disabled.
- No recurring PAPER authorization or full-evaluation cadence is shown.

#### PAPER EXECUTION
- The selected instrument is monitored continuously.
- CATS may initiate a full evaluation on the configured cadence when the existing prerequisites are satisfied.
- PMA proposes Portfolio intent.
- PMS is used when required.
- SYS validates the proposed action.
- Only a SYS `PASS` may continue to TEA/TES and Alpaca PAPER.
- The operator authorizes PAPER execution for the running system session; this authorization does not bypass SYS.

Internally, the existing tested runtime values (`MANUAL_TRIGGER_ONLY` and `AUTO_PAPER_EXECUTION`) remain implementation details so the Step 21 runtime does not need to be redesigned. They are no longer presented as operator modes.

### UI changes
- Removed the `Trading Activation` section.
- Removed `MANUAL EVALUATION` / `AUTO PAPER EXECUTION` from the operator UI.
- The System sidebar no longer shows `Activation`.
- PAPER EXECUTION directly exposes `Full Evaluation Cadence`.
- PAPER authorization text now explicitly states that PMA proposes and SYS approves.
- Main Operating Loop uses `Full Evaluation Cadence` and `Last Full Evaluation` instead of Auto/Activation terminology.
- Mode notices are shorter and state the SYS gate clearly.
- Additional Evidence wording no longer presents AUTO PAPER EXECUTION as a separate mode.

### Flow Explorer stabilization
- On first load, the newest persisted flow for the selected instrument is selected automatically.
- When a new flow appears, the UI switches to that new flow once.
- After that, the operator may manually select an older flow without the UI continuously forcing the latest one.
- The latest flow is labeled `Selected Flow — CURRENT / LATEST`.
- Older selections are labeled `Selected Flow — HISTORICAL`.
- The TAA card follows the same distinction: `Current Flow Assessment` vs `Historical Flow Assessment`.

### Backlog — not implemented in this patch
Owner Order Notification remains on the backlog:

- trigger after a PAPER order is committed/accepted by the broker;
- test recipient: `zybeldev@gmail.com`;
- notification failure must be non-blocking and must never alter or duplicate broker execution.

Email delivery is intentionally not implemented in Step 22 because UI stabilization remains the current priority.

### Validation performed while building this patch
- `scripts/streamlit_dashboard.py` Python compilation: PASS
- source assertions for two-mode UI: PASS
- source assertions for newest-flow auto-selection/current-vs-historical labeling: PASS

### Apply
Stop the running CATS system and Streamlit process first.

```bash
cd ~/cats_v2et

unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_22_Two_Mode_Operation_and_Latest_Flow.zip

unset CATS_SYS_PROFILE
unset CATS_EXECUTION_ACTIVATION
unset CATS_AUTO_PAPER_CONFIRM
unset CATS_AUTO_PAPER_SECONDS

python -m pytest -q
```

After the regression passes, restart the PAPER test profile:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

Then choose only one of the two operating modes:

```text
EVALUATION / MONITORING
PAPER EXECUTION
```

For PAPER EXECUTION, set the cadence, authorize the PAPER session, and load CATS.
