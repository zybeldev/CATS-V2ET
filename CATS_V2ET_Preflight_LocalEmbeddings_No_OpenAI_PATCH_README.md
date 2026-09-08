# CATS V2ET — Preflight Local Embeddings / No OpenAI Requirement Patch

## Purpose
Align the external preflight with the current V2ET reference runtime:

- Qwen is the injected reasoning model for the tested PAPER path.
- FastEmbed + ONNX Runtime provides local CPU embeddings.
- OpenAI is not required by this selected runtime configuration.

## Changes

### scripts/environment_doctor.py
Calls:

```python
inspect_environment(require_openai=False)
```

The existing runtime environment doctor therefore reports an absent OpenAI key as:

```text
OpenAI API key: Not required by selected runtime providers
```

instead of failing readiness.

### scripts/external_run_preflight.py
Replaces:

```text
OpenAI smoke test
```

with:

```text
Local CPU embedding smoke test
```

The preflight sequence is now:

1. Environment doctor
2. PostgreSQL connectivity
3. Database migrations
4. Schema verification
5. Alpaca PAPER smoke test
6. Local CPU embedding smoke test

The final banner is:

```text
CATS V2ET external run preflight: PASS
```

### tests/test_external_run_preflight_manifest.py
Updates the manifest expectation so the local embedding smoke test is required and the OpenAI smoke test is absent.

## Validation
Focused tests executed against the current patched source snapshot:

```text
9 passed
```

The environment doctor was also executed with no OPENAI_API_KEY and correctly returned readiness PASS when the selected runtime does not require OpenAI.

## Safety
This patch does not submit broker orders. The local embedding smoke test explicitly has no broker/order side effects.
