# CATS V2ET — Streamlit UI Step 07

## Purpose
Turn the Streamlit capstone report into a bounded human execution-entry point for the existing CATS PAPER runtime.

The UI now accepts:

- Financial Instrument ticker, e.g. `AAPL`
- Public website evidence URL, or
- Local evidence file (`TXT`, `MD`, `HTML`, `HTM`, `DOCX`)
- Explicit PAPER execution confirmation

The `RUN CATS PAPER` control invokes the existing `scripts/first_real_paper_flow.py` launcher. It does not create portfolio intent itself and it does not bypass CATS authority.

The authority chain remains:

`TAA -> PMA -> PMS -> SYS -> TEA -> TES`

The UI is only the human initiation boundary plus the persisted reporting surface.

## Safety boundary

The execution button is enabled only when:

- `CATS_ENVIRONMENT=PAPER`
- `QWEN_ENDPOINT_URL` is loaded
- `CATS_QWEN_SESSION_TOKEN` is loaded
- the user explicitly checks the PAPER confirmation box

The launcher is invoked with an argument list, not a shell command.

A run may submit an Alpaca PAPER order if the existing CATS authority chain decides execution is required.

## Local-file compatibility path

The current production launcher accepts evidence through `--evidence-url`. To avoid changing the CATS runtime architecture in this UI step, local files are staged under:

`.cats_ui_evidence/<content-hash>/`

Text/Markdown/DOCX files are converted to a local HTML evidence document. HTML files are preserved. The staged document is passed to the existing launcher as a `file://` URI.

The original file is preserved beside the staged evidence document and the staged text includes the original filename and SHA-256 content hash.

This is a UI compatibility mechanism; it does not alter PMA/PMS/SYS/TEA/TES behavior or authority.

## Result behavior

After a successful run, Streamlit clears its database read cache, identifies the newest persisted flow, and automatically opens that flow in the existing report.

The launcher stdout/stderr remains available in a collapsed `Last CATS launcher output` section for demonstration/debugging.

## Files

- `scripts/streamlit_dashboard.py`
- `src/cats/ui/execution_entry.py`
- `src/cats/ui/__init__.py`
- `tests/test_ui_execution_entry.py`

## Verification

The Step 07 execution-entry helper tests pass independently:

`6 passed`

If the applied Step 06 project baseline is `125 passed`, the expected full-suite baseline after Step 07 is `131 passed`.

Do not press `RUN CATS PAPER` merely to test the UI when the market is closed or when an actual PAPER execution is not intended. Use the unit suite for installation verification.
