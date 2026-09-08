# CATS V2ET — Streamlit UI Step 11

## Operator Hierarchy and Flow Decomposition

This patch is a presentation-layer refinement built on Step 10. It does not change CATS authority, portfolio logic, execution semantics, persistence, or the RunPod/Qwen runtime.

### Main layout changes

- Moves the **System** status card to the top of the left sidebar.
- Consolidates the duplicate read-only / PAPER-execution guidance into one sidebar note.
- Keeps the **CATS Components** aide in the sidebar, showing acronym, full component name, responsibility, and current state.
- Moves **CATS V2ET — Autonomous Trading System** to the visual top of the main page and reduces top whitespace.
- Replaces free-form instrument entry with a predefined technology-company equity selector.
- Locks the selected instrument while the monitoring loop is running.
- Shows company names with symbols, for example `AAPL (Apple)` and `NVDA (NVIDIA)`.

### Live operating order

1. **CATS System** / Financial Instrument
2. **Main Operating Loop**
3. **TSS | Market Surveillance — SYMBOL (Company)**
4. **TSS | Signal Assessment — SYMBOL (Company)**
5. **TAA | Latest Alpaca News — SYMBOL (Company)**
6. **TAA | Additional Evidence / Run CATS — PAPER**
7. **TAA | Monitoring — SYMBOL (Company)**

The signal-assessment card now includes **Assessment Date Time** using the operator-friendly local display convention while preserving persisted UTC/TIMESTAMPTZ values internally.

### Persisted flow-report order

1. **Selected Flow**
2. **TAA | Financial Assessment**
3. **PMA | Decision**
4. **SYS | Verification**
5. **TEA | Execution Behavior — Portfolio**
6. **CATS | Authority / Material Flow**
7. **DB | Recent Flow History**
8. **Open Alpaca PAPER** link
9. **DB | Technical Records**

The earlier combined execution card is decomposed so PMA, SYS, and TEA are visibly separated according to their CATS responsibilities.

### Authority visibility

The Main Operating Loop now displays the CATS authority path:

`TAA → PMA → SYS → TEA → TES`

and separately shows the current activation state, such as `MANUAL_TRIGGER_ONLY` during monitoring.

### Architectural note

The live **Market Surveillance** card is labeled `TSS`, not `TAA`, because it displays deterministic market measurements owned by the Trading Signal Service. TAA remains responsible for financial interpretation, news/evidence interpretation, and monitoring assessments.

### Apply

Apply from the CATS project root after Step 10:

```bash
unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_11_Operator_Hierarchy.zip
python -m pytest -q
streamlit run scripts/streamlit_dashboard.py
```

Before replacing the UI file, stop the Streamlit process. Stop the CATS main loop first if you want to change the selected Financial Instrument.
