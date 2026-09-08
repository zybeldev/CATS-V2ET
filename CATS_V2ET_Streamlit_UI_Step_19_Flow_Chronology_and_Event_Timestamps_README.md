# CATS V2ET Streamlit UI — Step 19
## Flow Chronology and Event Timestamps

Purpose: make the Selected Flow display chronologically coherent and show when each persisted CATS stage occurred.

### Changes

- Adds `Selected Flow | Event Timeline`.
- Timeline rows are sorted by the actual persisted event timestamp.
- Missing historical timestamps display `NOT RECORDED`; the UI does not estimate or manufacture times.
- TAA card shows Assessment Date Time.
- PMA card shows Decision Date Time.
- SYS card shows Verification Date Time.
- TEA card shows Execution Action Date Time and Execution Completed Date Time.
- TES card shows Order Submitted Date Time, Fill Date Time, and Reconciliation Date Time.
- Timeline also shows Flow Started, Portfolio State Accepted, and Flow Completed when those timestamps exist.
- For historical schemas without a timestamp on `TES_Order`, the linked `TEA_Execution_Action.requested_at` is used as the safe order-submission fallback. In the current persistence path that value is populated from broker `submitted_at` when available.
- Historical records are never rewritten.

### Authority and behavior

This is a read-only Streamlit observability change. It does not change:

- TAA reasoning;
- PMA Portfolio authority;
- SYS validation;
- TEA execution authority;
- TES broker behavior;
- Alpaca orders;
- persisted CATS state.

### Apply

```bash
cd ~/cats_v2et
unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_19_Flow_Chronology_and_Event_Timestamps.zip
python -m pytest -q
streamlit run scripts/streamlit_dashboard.py
```

If the aggressive PAPER testing profile is being used for the runtime, enable it only after the regression suite:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

### Build verification

- `scripts/streamlit_dashboard.py` Python syntax compilation: PASS.
- Timeline helper smoke test: PASS.
