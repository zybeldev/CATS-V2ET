# CATS V2ET — Streamlit UI Step 05

## Purpose
Replace wide metric-column presentation with a report-style, line-by-line human observability layout.

## Presentation changes
- System status: one fact per line.
- Selected flow: one fact per line.
- TAA assessment: horizon, assessment, confidence, status, and narrative in a report card.
- Execution behavior: current position, target, required change, PMA, SYS, TEA, broker, and reconciliation presented line by line.
- US-dollar equivalents remain beside the corresponding share quantities when a persisted TSS reference price exists.
- CATS Authority / Material Flow: one stage per line rather than six metric columns.
- Technical records remain available below for detailed trace inspection.

## Safety
Presentation only. The dashboard remains SELECT-only and does not call Alpaca, Qwen, retrieval providers, agents, or execution code.
