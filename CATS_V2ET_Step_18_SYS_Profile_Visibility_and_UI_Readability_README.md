# CATS V2ET — Step 18: SYS Profile Visibility and UI Readability

This patch continues CATS V2ET testing without changing the architecture.

## What changes

### 1. SYS aggressive PAPER profile correction

The aggressive PAPER test profile now uses:

- maximum position weight: 25%
- maximum total equity exposure: 99%
- minimum cash reserve: 1%
- maximum order value: $50,000
- maximum order quantity: 5,000 shares

The 99% equity ceiling preserves the PMS invariant that total equity exposure cannot exceed capital remaining after the minimum cash reserve.

The profile remains PAPER-only and does not bypass SYS direction validation, provenance/lineage requirements, fail-closed behavior, or broker reconciliation.

### 2. SYS behavior profile is visible in the application

When:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
```

the dashboard displays:

```text
SYS Behavior Profile  AGGRESSIVE — PAPER TEST
```

It is shown in the sidebar System card and in the Main Operating Loop card. A visible warning also explains that the more permissive limits are for PAPER execution testing.

When the variable is unset, the application displays:

```text
SYS Behavior Profile  NORMAL
```

### 3. Live highlight duration

Live timestamp/value highlighting now lasts 5 seconds instead of 1 second.

### 4. News and assessment readability

- News headline is visually separated with its own heading background.
- News narrative/body text uses a white reading surface.
- TAA reasoning/assessment narrative uses a white background.
- Assessment subsections use white reading surfaces with visually distinct subsection labels.

### 5. Runtime UI cleanup

The implementation-history sentence beginning with `Step 09` is removed from the Main Operating Loop. The runtime UI now describes current behavior only.

## Apply

Stop Streamlit first.

Place this ZIP in:

```text
/home/zybeldev/V2et_ConstructingSteps_and_Patches
```

Then:

```bash
cd ~/cats_v2et

unzip -o ~/V2et_ConstructingSteps_and_Patches/CATS_V2ET_Patch_Step_18_SYS_Profile_Visibility_and_UI_Readability.zip

unset CATS_SYS_PROFILE
python -m pytest -q
```

Run the normal regression suite with the temporary aggressive profile unset.

If the regression suite passes, enable the PAPER test profile and launch the dashboard:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
streamlit run scripts/streamlit_dashboard.py
```

To return to normal behavior:

```bash
unset CATS_SYS_PROFILE
streamlit run scripts/streamlit_dashboard.py
```

## Verification performed while preparing this patch

- `streamlit_dashboard.py` Python syntax compilation: PASS
- `configuration.py` Python syntax compilation: PASS
- focused SYS aggressive-profile tests: 4 PASS

## Still separate from this UI patch

The previously identified TAA evidence-grounding defect for uploaded local evidence is not changed here. It remains a functional testing item and should be corrected independently so the assessment explicitly reflects material facts in the supplied evidence.
