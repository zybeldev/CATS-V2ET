# CATS V2ET — Streamlit UI Step 03

## Purpose

Correct the human-facing TAA presentation without changing CATS behavior or persisted state.

## Changes

- Normalizes historical TAA persistence where `assessment_type` carried `TACTICAL` / `STRATEGIC`.
- Presents that value under **Horizon**.
- Presents the TAA record as a **CANDIDATE** assessment for those historical flows.
- Recovers the narrative from compatible persisted field names such as `summary`, `assessment_summary`, `assessment`, `rationale_summary`, or `rationale`.
- Keeps the raw persistence visible in Technical Records.
- Keeps the UI SELECT-only.

## Safety

The dashboard still performs no Alpaca calls, no Qwen calls, no retrieval execution, no agent execution, no order submission, and no database writes.

## Expected regression baseline

Step 03 adds two UI read-model tests. If Step 02 was at 118 passing tests, the expected baseline is **120 passed**.
