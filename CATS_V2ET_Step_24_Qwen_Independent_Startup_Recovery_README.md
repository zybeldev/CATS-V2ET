# CATS V2ET — Step 24: Qwen-Independent Startup Recovery

## Purpose

Correct the Streamlit startup order so deterministic broker reconciliation runs before any Qwen readiness requirement.

## Startup sequence

```text
LOAD CATS SYSTEM
    -> verify PAPER environment
    -> PostgreSQL + Alpaca startup recovery
    -> reconcile persisted non-terminal PAPER flows
    -> persist/verify broker-confirmed reality
    -> if recovery BLOCKED: stop startup
    -> if Qwen unavailable: remain NOT READY for normal reasoning, but recovery is complete
    -> if Qwen ready: validate new-work controls and run preflight
    -> start normal monitoring / evaluation loop
```

## Architectural effect

Recovery no longer depends on Qwen. Qwen remains required for new TAA/PMA reasoning and the normal operating loop, but not for deterministic reconstruction and reconciliation of already-persisted execution state.

The recovery-only helper never submits a replacement order. It delegates to the Step 23 persisted-flow recovery path.

## Files

- `scripts/streamlit_dashboard.py`
- `scripts/cats_startup_recovery.py`
- `tests/test_streamlit_startup_recovery_sequence.py`

This patch is intentionally small and assumes Step 23 startup-recovery runtime code is already applied.

## Apply

```bash
cd ~/cats_v2et
unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Step_24_Qwen_Independent_Startup_Recovery.zip
python -m pytest -q
streamlit run scripts/streamlit_dashboard.py
```

## Expected behavior with RunPod/Qwen stopped

Press `LOAD CATS SYSTEM`.

CATS should first perform startup recovery against PostgreSQL and Alpaca. If the suspended Sep 4 execution is now broker-confirmed as filled, the original persisted flow should be reconciled/finalized without any new submission. After recovery, Streamlit may report Qwen as unavailable and leave the normal operating loop stopped. That is expected.
