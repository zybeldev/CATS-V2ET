# CATS V2ET — Source Freshness and Flow Visibility Patch

## Purpose

This patch implements two V2ET requirements without changing CATS authority boundaries:

1. **TAA source-date / freshness awareness**
2. **Descriptive end-to-end vertical-slice visibility for CLI and future UI use**

The patch does **not** change PMA/PMS/SYS/TEA/TES authority and does not change broker execution policy.

## Source-Date / Freshness Behavior

For public-web evidence:

- `observed_at` is used as the source publication/source-observation time when known.
- `retrieved_at` remains the time CATS acquired the source.
- The public evidence adapter attempts conservative publication-date extraction from common structured metadata (`datePublished`, `article:published_time`, and `<time datetime=...>`).
- If no reliable source date is found, the evidence is marked `SOURCE_DATE_UNKNOWN` rather than pretending the retrieval time is the publication time.

Freshness is classified for observability as:

- `SAME_DAY`
- `RECENT_7D`
- `AGING_30D`
- `HISTORICAL`
- `SOURCE_DATE_UNKNOWN`
- `SOURCE_DATE_IN_FUTURE`

These categories do **not** decide truth or relevance. TAA is explicitly instructed to judge source age relative to the requested `TACTICAL` or `STRATEGIC` horizon and to reflect material freshness uncertainty in the assessment/confidence.

The source date remains metadata; it is not mixed into the semantic embedding vector.

## Flow Visibility

`FlowVisibilityReport` is a structured read-model with both:

- `as_dict()` for a future UI/API; and
- `render_text()` for the current terminal operator experience.

The normal PAPER launcher now exposes the vertical slice as descriptive stages:

1. Starting Portfolio State
2. Market State — TSS
3. Input / Evidence
4. TAA Assessment
5. PMS Portfolio Alternative
6. PMA Decision
7. SYS Validation
8. TEA Execution
9. Broker Result
10. Reconciliation
11. Accepted Portfolio State

The same visibility path also represents:

- `NO_CHANGE` / no execution;
- SYS rejection;
- execution uncertainty / recovery-required outcomes; and
- partial progress if an exception occurs.

## PMA / Execution Semantic Warning

The patch adds an **observability warning only** when the PMA decision label and the actual required portfolio delta point in opposite directions, for example:

```text
PMA decision: BUY_OR_INCREASE
required quantity delta: negative
semantic_consistency: WARNING_BUY_INTENT_REQUIRES_SELL_DELTA
```

This intentionally does **not** change portfolio intent or block execution in this patch. It makes the inconsistency visible so it can be analyzed explicitly rather than hidden in persistence records.

## Files Added / Modified

- `src/cats/adapters/evidence/public.py`
- `src/cats/agents/taa/agent.py`
- `src/cats/retrieval/models.py`
- `src/cats/runtime/production_persistence.py`
- `src/cats/runtime/production_paper_flow.py`
- `src/cats/runtime/flow_visibility.py` **(new)**
- `src/cats/runtime/__init__.py`
- `scripts/first_real_paper_flow.py`
- focused tests for source date, TAA freshness, visibility, and semantic warning

## Validation Performed on the Supplied Archive

Focused modified-path tests:

```text
10 passed
```

Broader supplied-source test run, excluding tests that require scripts not included in the uploaded archive:

```text
85 passed, 1 skipped
```

The excluded failures were caused by the uploaded archive containing only `scripts/first_real_paper_flow.py` while several existing tests reference other project scripts. They were not failures in this patch.

## Apply to the Full Local Project

From `~/cats_v2et`:

```bash
unzip -o ~/CATS_V2ET_Patch_SourceFreshness_and_FlowVisibility.zip
python -m pytest -q
```

Applying the patch and running pytest does **not** submit a PAPER order.

Do not rerun the PAPER flow merely to test this patch. The prior AAPL run already exposed a PMA `BUY_OR_INCREASE` versus SELL-delta semantic inconsistency; use the test suite first and resolve that behavior deliberately before another PAPER execution.

## Not Included in This Patch

The current embedding provider remains unchanged. Migration from OpenAI embeddings to a local/open CPU embedding model is a separate implementation step behind the existing embedding-provider interface.
