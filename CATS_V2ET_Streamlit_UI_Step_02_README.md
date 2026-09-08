# CATS V2ET — Streamlit UI Step 02

## Purpose

Make the capstone dashboard human-readable by emphasizing the two behaviors most useful to explain CATS:

1. **TAA reasoning** — horizon, confidence, assessment type, and persisted reasoning/assessment summary.
2. **Execution behavior** — current position, PMA/PMS target, required change, SYS/TEA/broker result, reconciliation, and certainty.

## Human-readable position values

Equity quantities remain authoritative CATS quantities. The UI additionally calculates display-only US-dollar equivalents using the best persisted TSS price measurement from the selected flow.

Conceptually:

```text
current shares x persisted TSS reference price = approximate current US$ value
target shares  x persisted TSS reference price = approximate target US$ value
delta shares   x persisted TSS reference price = approximate change in US$
```

These values are presentation projections only. The UI does not call a live market-data provider and does not modify CATS state.

## Read-only boundary

The dashboard remains SELECT-only:

- no Alpaca calls;
- no order submission;
- no Qwen calls;
- no retrieval execution;
- no agent invocation;
- no database writes.

Raw technical records remain available in collapsed expanders, but no longer dominate the default presentation.
