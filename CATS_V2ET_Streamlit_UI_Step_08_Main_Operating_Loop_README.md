# CATS V2ET — Streamlit UI Step 08: Main Operating Loop

## Purpose

Step 08 changes the V2ET demonstration from a one-shot/static vertical slice into a continuously observing runtime while preserving the existing CATS authority chain.

`LOAD CATS SYSTEM` now performs the existing external-run preflight and starts a background CATS main operating loop.

The loop:

- monitors the current Alpaca PAPER portfolio plus optional configured symbols;
- reads current/latest Alpaca market data;
- calculates existing TSS deterministic measurements;
- reads Alpaca market news for the monitored universe;
- publishes a small operational status projection for the Streamlit console; and
- continues until `STOP CATS SYSTEM` is requested.

## Authority boundary

Step 08 does **not** introduce a new trading authority path and does **not** automatically submit orders from the monitoring loop.

The existing `RUN CATS PAPER` entry remains the explicit one-cycle trigger for the tested CATS authority chain:

`TSS / evidence -> TAA -> PMA/PMS -> SYS -> TEA/TES -> Alpaca PAPER (only if authorized)`

This separation lets the capstone observe dynamic market/news behavior before separately deciding how material events should activate the existing authority chain.

## Qwen readiness

The Streamlit console now probes the Qwen `/health` endpoint. A configured but stale Cloudflare tunnel is shown as `UNREACHABLE`, not `READY`.

`LOAD CATS SYSTEM` is blocked until Qwen is actually reachable.

## Launcher errors

The manual `RUN CATS PAPER` path now shows concise descriptive errors for common failures (for example stale Qwen or HTTP 403 evidence access), while preserving technical output in the existing expander.

## Runtime defaults

- Market cycle: 60 seconds
- News refresh: 3600 seconds (hourly; first check occurs immediately)
- News lookback: 120 minutes
- Market lookback: 90 days
- Monitoring universe: current Alpaca positions plus optional `CATS_MONITOR_SYMBOLS`

Optional environment overrides:

- `CATS_MONITOR_SYMBOLS=AAPL,NVDA`
- `CATS_MAIN_LOOP_MARKET_SECONDS=60`
- `CATS_MAIN_LOOP_NEWS_SECONDS=3600`
- `CATS_MAIN_LOOP_NEWS_LOOKBACK_MINUTES=120`

The `.cats_runtime/main_loop_status.json` file is an observability projection only. It is not authoritative portfolio state.

## Apply

From `~/cats_v2et`:

```bash
unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_08_Main_Operating_Loop.zip
python -m pytest -q
streamlit run scripts/streamlit_dashboard.py
```

Before pressing `LOAD CATS SYSTEM`, ensure the Colab Qwen endpoint is running and the current `QWEN_ENDPOINT_URL` and `CATS_QWEN_SESSION_TOKEN` are loaded in the shell that starts Streamlit.

## Verification performed during patch construction

Uploaded baseline: `128 passed, 1 skipped`.

Step 08 working copy: `135 passed, 1 skipped`.

No live/PAPER order was submitted during patch tests; new tests use fakes for loop and UI-control behavior.
