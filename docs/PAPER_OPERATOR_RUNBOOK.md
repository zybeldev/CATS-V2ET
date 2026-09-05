# CATS V2E — PAPER Operator Runbook

Construction Step 18 provides one operational entrypoint and post-run verification.

## Database preflight

```bash
python scripts/paper_operator.py database-preflight
```

## External dependency preflight

```bash
python scripts/paper_operator.py external-preflight
```

## Execute one PAPER flow

```bash
python scripts/paper_operator.py run \
  --symbol AAPL \
  --evidence-url <PUBLIC_EVIDENCE_URL> \
  --confirm-paper
```

The explicit confirmation flag is mandatory.

## Verify the latest persisted flow

```bash
python scripts/paper_operator.py verify-latest
```

Verification fails closed unless:

- the `TRACE_Flow` is `COMPLETED`;
- Evidence and Assessment are present;
- PMS OptimizationRequest and PortfolioAlternative are present;
- PMA PortfolioDecision is present;
- SYS ValidationResult is `PASS`;
- TEA Execution and ExecutionResult are present;
- TES Order is present;
- reconciliation is present;
- an accepted PMA Portfolio State exists;
- provenance and lineage exist;
- no execution remains `UNKNOWN_OUTCOME`.

## Verify a specific flow

```bash
python scripts/verify_flow.py --flow-id <FLOW_ID>
```

This gives the capstone a mechanically verifiable audit trail instead of relying on console output from the run.
