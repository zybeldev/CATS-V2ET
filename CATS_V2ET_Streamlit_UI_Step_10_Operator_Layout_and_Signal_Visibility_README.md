# CATS V2ET — Streamlit UI Step 10

## Operator Layout and Signal Visibility

This patch builds directly on Step 09 and keeps the CATS authority model unchanged.

### What changes

1. **One shared Financial Instrument selector at the top**
   - Used by both continuous monitoring and RUN CATS PAPER.
   - Locked while the main operating loop is running.
   - V2ET monitoring runs one selected instrument per cycle.
   - Stop the system, change the instrument, and load again to switch.

2. **Main CATS components visible in the Flow Explorer sidebar**
   - TSS — Trading Signal Service
   - TAA — Trading Assessment Agent
   - PMA — Portfolio Management Agent
   - PMS — Portfolio Management Service
   - SYS — System Validation Authority
   - TEA — Trading Execution Agent
   - TES — Trading Execution System
   - DAS — Derivatives Analysis Service (not instantiated in V2ET)
   - Each component shows a concise current operating state / responsibility.

3. **TSS Signal Assessment card**
   - Shows deterministic classifications derived from the existing TSS measurements.
   - 1-period return direction.
   - Momentum direction.
   - Price relative to short SMA.
   - Short SMA relative to long SMA.
   - Annualized volatility.
   - Liquidity proxy.
   - Explicitly states that this is not a BUY/SELL recommendation.

4. **News independence is clearer**
   - Latest Alpaca News now shows monitoring state, last check result, last check time, source, symbol, publication time, and headline.
   - Main loop tracks whether a news refresh is INITIAL, NEW, UNCHANGED, or NO_NEWS.
   - Market/TSS scanning and TAA reassessment continue independently of new news.

5. **Operator-readable timestamps**
   - UTC/TIMESTAMPTZ persistence is unchanged.
   - Streamlit displays operator timestamps such as:

     `Sep 3, 2026   12:59:53 PM MST`

   - Default UI timezone: `America/Phoenix`.
   - Optional override: `CATS_UI_TIMEZONE=<IANA timezone>`.

6. **Evidence moved conceptually below live assessment**
   - The lower section is renamed `Additional Evidence / Run CATS — PAPER`.
   - It uses the same selected Financial Instrument from the top of the page.

### Authority remains unchanged

Monitoring mode remains:

```text
TSS measures
  ↓
TAA interprets
  ↓
STOP
```

`RUN CATS PAPER` remains the explicit trigger for the full authority chain.

### Apply

Stop the current CATS main loop first. Stop Streamlit with Ctrl+C, then from `~/cats_v2et`:

```bash
unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_10_Operator_Layout_and_Signal_Visibility.zip
python -m pytest -q
```

Then reload environment variables and start Streamlit:

```bash
set -a
source .env
set +a
export QWEN_ENDPOINT_URL='http://127.0.0.1:18000/reason'
streamlit run scripts/streamlit_dashboard.py
```

The existing `CATS_QWEN_SESSION_TOKEN` must already be present in the shell, as in Step 09. Do not print or paste it.
