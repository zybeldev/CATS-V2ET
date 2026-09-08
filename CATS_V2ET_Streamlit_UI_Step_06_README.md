# CATS V2ET Streamlit UI — Step 06

## Purpose

Complete the human-readable execution presentation for historical and current CATS flows without changing CATS behavior.

## Changes

- Reconstructs broker/material records through the persisted CATS relational lineage when child tables intentionally do not duplicate `flow_id`.
- Links `TES_Order`, `TES_Fill`, `TEA_Reconciliation`, `TEA_Execution_Result`, and accepted `PMA_Portfolio_State` records back to the selected flow.
- Uses persisted TSS price as the preferred UI valuation price.
- When an older flow has no persisted TSS price, uses the broker-confirmed fill price from the same execution lineage as a clearly labeled display-only fallback.
- Shows current, target, required-change, and final-position US$ equivalents where a persisted historical price/value exists.
- Shows broker order, fill, trade value, reconciliation result/certainty, and accepted final position in the report-style layout.
- Technical record expanders now include indirectly linked material records as well as tables containing `flow_id` directly.

## Safety

This patch is read-only UI/read-model code. It does not call Alpaca, Qwen, retrieval providers, agents, or execution code and does not write to PostgreSQL.

## Tests

Four additional read-model tests cover indirect execution lineage, broker-fill valuation fallback, reconciliation/final position reconstruction, and material-flow summaries.
