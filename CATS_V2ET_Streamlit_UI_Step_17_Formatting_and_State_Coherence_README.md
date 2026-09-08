# CATS V2ET — Streamlit UI Step 17

## Formatting and State Coherence

This patch is a presentation and operator-state refinement built on Step 16. It does not change the CATS architecture, authority model, Portfolio logic, broker adapter, database schema, reasoning contract, or trading rules.

### Changes

1. Removes the duplicated explanatory paragraph beneath the sidebar LOAD/STOP control.
2. Changes live timestamp highlighting from a permanent yellow background to a one-second refresh pulse that appears only when the underlying value changes.
3. Places TAA reasoning / assessment narratives in a neutral light-gray panel for both live monitoring and selected-flow assessments.
4. Makes historical flow views instrument-coherent:
   - changing the Financial Instrument clears the previous flow selection;
   - Flow Explorer shows only persisted flows for the selected instrument;
   - Selected Flow, TAA/PMA/SYS/TEA/TES, Authority / Material Flow, Recent Flow History, and Technical Records all follow the selected instrument;
   - if the selected instrument has no persisted full flow, the UI reports that state instead of showing another instrument's history.
5. Updates the PAPER execution-entry wording to reflect system semantics:
   - section title becomes `CATS | Additional Evidence / Full Evaluation`;
   - button becomes `RUN CATS EVALUATION`;
   - confirmation states that CATS may execute through Alpaca PAPER only if the system determines an order is required.
6. Moves Evidence Source selection outside the Streamlit form so choosing `Website URL` or `Local File` immediately rerenders the correct input control.
7. Keeps `PAPER EXECUTION` as an enablement state only; the system still determines whether a Portfolio change or broker order is required.

### Validation performed

- `python -m py_compile scripts/streamlit_dashboard.py` — PASS
- Full project regression suite was not run in the patch-build container.

### Apply

Stop Streamlit first, then from `~/cats_v2et`:

```bash
unzip -o \
  ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_17_Formatting_and_State_Coherence.zip

python -m pytest -q

streamlit run scripts/streamlit_dashboard.py
```
