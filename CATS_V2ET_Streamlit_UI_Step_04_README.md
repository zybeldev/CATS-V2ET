# CATS V2ET — Streamlit UI Step 04

## Purpose

Make the capstone dashboard denser and easier to read while correcting the remaining historical TAA label edge case.

## Changes

- Reduces oversized Streamlit metric values and headings.
- Keeps TAA narrative/body text at a normal reading size.
- Reduces truncation pressure in the status and execution summary rows.
- Corrects historical rows where both `assessment_type` and `horizon` contain `TACTICAL`/`STRATEGIC`: the UI presents **Horizon = TACTICAL/STRATEGIC** and **Assessment = CANDIDATE**.
- Changes presentation only; no CATS operational behavior or persisted state is modified.

## Safety

The dashboard remains SELECT-only: no Alpaca calls, no Qwen calls, no retrieval execution, no agent execution, no order submission, and no database writes.

## Expected regression baseline

Step 04 adds one UI read-model regression test. If Step 03 was at 120 passing tests, the expected project baseline is **121 passed**.
