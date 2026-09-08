# CATS V2ET — Streamlit UI Step 20

## Chronology Consistency and Historical Clarity

Presentation-only patch. No CATS authority or architecture is changed.

### Changes

- Historical selected flows are explicitly labeled `HISTORICAL`.
- Historical TAA card is labeled `Historical Flow Assessment`.
- Event Timeline follows the canonical CATS causal sequence.
- Events that share the same displayed second retain causal order instead of being reordered by hidden microseconds.
- Missing historical timestamps remain in their correct causal position as `NOT RECORDED`.
- A warning is shown in the timeline note if a persisted timestamp moves backward across displayed seconds.
- Live TAA `Last Refresh` is renamed `Assessment Date Time`.
- Raw ISO timestamps inside TAA narrative prose are rendered in operator-local time; an internal repeated assessment timestamp is replaced by `this assessment` so the card metadata remains authoritative.
- Recent Flow History timestamps are converted from persisted UTC to the same operator-local display format used by the cards.
- Long labels are shortened: `Decision Time`, `Verification Time`, `Action Time`, `Completed Time`, `Submitted`, `Filled`, `Reconciled`.
- Long report labels may wrap instead of colliding with values.
- Historical TSS lineage wording now distinguishes TSS values carried in assessment context from a directly persisted TSS row link.
- PMA/SYS/TEA/TES explanatory text is shortened for demo readability.

### Deliberately unchanged

- Persisted timestamps remain unchanged in PostgreSQL.
- No historical record is rewritten.
- CATS authority remains TAA -> PMA -> SYS -> TEA -> TES.
- The TAA `valid_until` policy is not changed by this UI patch.

### Validation

- `python -m py_compile scripts/streamlit_dashboard.py` — PASS during patch construction.
