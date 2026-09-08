# CATS V2ET — Streamlit UI Step 12

## Flow Clarification and Sidebar Control

This patch is presentation-only and builds on Step 11.

### Changes

- Moves LOAD / STOP CATS SYSTEM into the left System area.
- Uses the primary/red control styling for the active system control.
- Improves top-page spacing so the CATS V2ET title is fully visible.
- Keeps one shared Financial Instrument selector on the main page.
- Keeps the CATS Components reference in operational order.
- Expands Main Operating Loop flow visibility:
  - Authority Chain: TAA → PMA → SYS → TEA → TES
  - Market Signal Flow: Alpaca → TSS → TAA
  - Optimization: PMA ↔ PMS (when required)
  - Broker Interface: TEA → TES ↔ Alpaca
- Clarifies that the selected-flow TAA Financial Assessment is the full-cycle assessment supplied to PMA; it is RAG-grounded when retrieved evidence is used.
- Splits execution presentation into:
  - TEA | Execution Action
  - TES | Alpaca Order
- Changes the Alpaca link to:
  - https://app.alpaca.markets/account/activities

### Architecture preserved

No CATS runtime authority or trading behavior is changed.

TSS remains deterministic measurement/classification. TAA interprets. PMA decides. PMS optimizes when required. SYS validates. TEA determines execution action. TES performs broker-facing execution mechanisms.
