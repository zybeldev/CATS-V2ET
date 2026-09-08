# CATS V2ET — SYS Aggressive PAPER Test Profile

Purpose: temporarily make the governed PAPER test envelope more permissive so valid PMA portfolio-change decisions are more likely to proceed through SYS and exercise TEA/TES/Alpaca PAPER execution.

This patch does **not** change CATS architecture and does **not** allow SYS to originate Portfolio intent. PMA still decides whether a Portfolio change exists. SYS remains deterministic validation authority.

## Profile

Set this environment variable before starting Streamlit:

```bash
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
```

The profile changes only bounded SYS/PMS operating limits used by the PAPER flow:

- maximum position weight: at least 25%
- maximum total equity exposure: 100%
- minimum cash reserve: 1%
- maximum order value: at least $50,000
- maximum order quantity: at least 5,000 shares

The profile remains PAPER-only and does not bypass:

- PAPER environment enforcement
- permitted instrument type
- PMA/SYS decision-direction consistency
- broker reconciliation
- provenance/lineage requirements
- fail-closed validation behavior

## Apply

Stop Streamlit first, then from the CATS V2ET project root:

```bash
cd ~/cats_v2et
unzip -o ~/CATS_V2ET_Patch_SYS_Aggressive_Paper_Test_Profile.zip
export CATS_SYS_PROFILE=AGGRESSIVE_PAPER_TEST
python -m pytest -q
streamlit run scripts/streamlit_dashboard.py
```

If your zip is in another directory, use that path instead.

## Return to normal SYS policy

Stop Streamlit, then:

```bash
unset CATS_SYS_PROFILE
streamlit run scripts/streamlit_dashboard.py
```

`NORMAL` remains the default when `CATS_SYS_PROFILE` is unset.

## Important testing interpretation

This profile removes conservative SYS/PMS barriers; it does not convert `PMA = NO_CHANGE` into a trade. If a full PAPER evaluation still produces no order, inspect the PMA Decision. A `NO_CHANGE` outcome means no executable Portfolio intent reached SYS, which is correct CATS behavior.
