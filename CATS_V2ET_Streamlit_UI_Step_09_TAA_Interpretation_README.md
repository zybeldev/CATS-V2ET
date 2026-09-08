# CATS V2ET — Streamlit UI Step 09: TAA Interpretation

Step 09 extends the Step 08 dynamic observation loop with the existing CATS Trading Assessment Agent (TAA) boundary.

## Behavior

The loaded CATS system now operates as:

```text
Alpaca market data -> TSS measurements ----\
                                         -> TAA monitoring assessment -> UI
Alpaca/Benzinga news -> local RAG --------/
```

The TAA monitoring path uses:

- existing `TradingAssessmentAgent`
- local FastEmbed CPU embeddings
- in-memory retrieval for the current Alpaca news window
- remote Qwen reasoning through the existing adapter
- TACTICAL horizon / CANDIDATE assessment semantics

## Authority boundary

Step 09 intentionally stops at TAA.

Monitoring assessments are **not** forwarded to PMA, PMS, SYS, TEA, TES, or Alpaca order submission. `RUN CATS PAPER` remains the explicit full authority-chain trigger.

## Cadence

Defaults:

- Market/TSS: 60 seconds
- Alpaca news: 3600 seconds
- TAA monitoring assessment: 300 seconds

Override the TAA cadence with:

```bash
export CATS_MAIN_LOOP_TAA_SECONDS=300
```

## UI

The Main Operating Loop card now shows the last TAA assessment timestamp and interpretation state. A new `TAA Monitoring — <SYMBOL>` report card shows:

- status
- monitoring-only mode
- horizon
- assessment type
- confidence
- assessment time
- validity
- evidence count
- Qwen inference time when available
- assessment narrative

TAA errors are isolated from market surveillance so a reasoning failure does not terminate the observation loop.
