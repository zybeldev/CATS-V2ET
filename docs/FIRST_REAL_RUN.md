# CATS V2ET — First Real PAPER Run Procedure

## 1. Configure environment

Required:

- `CATS_ENVIRONMENT=PAPER`
- `CATS_DATABASE_URL=postgresql+psycopg://...`
- `ALPACA_API_KEY=...`
- `ALPACA_API_SECRET=...`
- `ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets`
- `OPENAI_API_KEY=...`

## 2. Environment doctor

```bash
python scripts/environment_doctor.py
```

This is fail-closed. It rejects a non-PAPER Alpaca endpoint.

## 3. External preflight

```bash
python scripts/preflight_real_run.py
```

Runs:

1. PostgreSQL connectivity
2. database migrations
3. read-only Alpaca PAPER authentication/account check
4. OpenAI reasoning/embedding smoke test

## 4. Dry-run launcher

```bash
python scripts/first_real_paper_run.py --symbol AAPL --confirm-paper --dry-run
```

This verifies the real-run gate but does not submit an order.

## 5. Real order execution

Direct broker submission from the launcher is deliberately blocked.

The first real order must pass through the complete authority chain:

TAA -> PMA -> PMS when required -> SYS -> TEA -> TES -> Alpaca PAPER -> reconciliation -> PMA Portfolio State

Production wiring of that complete chain is the next construction step.
