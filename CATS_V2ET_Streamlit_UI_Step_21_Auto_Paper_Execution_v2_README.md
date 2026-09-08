# CATS V2ET Step 21 v2 — Auto PAPER Execution

## Purpose

Correct the Step 21 AUTO PAPER EXECUTION patch after regression testing exposed two separate issues.

## Diagnosis

The first three full-chain failures seen after Step 21 are caused by running the baseline regression suite while `CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST` is active. That profile intentionally relaxes SYS/PMS limits and therefore changes tests that expect normal governed limits.

The remaining two failures are Step 21 compatibility regressions in the main operating loop. Step 21 had been based on a stale main-loop snapshot and omitted later selected-instrument and news-status behavior.

## Corrections in v2

Restored without changing the AUTO PAPER EXECUTION design:

- `MainLoopConfig.selected_symbols_only`
- selected-instrument-only universe behavior
- `news_status`
- latest-news signature tracking
- `INITIAL`, `UNCHANGED`, `NEW`, and `NO_NEWS` news states
- publication of `news_status` in main-loop status
- `selected_symbols_only=bool(symbols)` in the main-loop launcher

AUTO PAPER EXECUTION remains as introduced in Step 21.

## Verification performed

Python compilation: PASS

Focused compatibility regression with SYS profile and AUTO environment overrides unset:

```text
8 passed
```

The focused suite covered the existing main operating loop tests plus the new AUTO PAPER EXECUTION tests.

## Apply

Stop CATS and Streamlit first.

```bash
cd ~/cats_v2et

unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Streamlit_UI_Step_21_Auto_Paper_Execution_v2.zip

unset CATS_SYS_PROFILE
unset CATS_EXECUTION_ACTIVATION
unset CATS_AUTO_PAPER_CONFIRM
unset CATS_AUTO_PAPER_SECONDS

python -m pytest -q
```

The baseline regression suite must run with the normal SYS profile. Do not enable the aggressive PAPER test profile until the baseline regression passes.

## Run AUTO PAPER execution after tests pass

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

Then select PAPER EXECUTION and AUTO PAPER EXECUTION in the Streamlit operator console, set the desired cadence, acknowledge recurring PAPER authorization, and load CATS.

## Authority boundary

AUTO mode initiates the existing full PAPER authority chain. It does not bypass PMA, SYS, TEA, TES, broker reconciliation, or Portfolio State acceptance.
