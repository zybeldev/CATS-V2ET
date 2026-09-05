# CATS V2E External Integration Readiness

Construction Step 10 prepares the codebase for real external integration.

## PostgreSQL

Commands:

```bash
python scripts/check_postgres.py
python scripts/run_migrations.py
```

The database URL is supplied through `CATS_DATABASE_URL`.

## Alpaca Paper Trading

Configure:

- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`

Then run:

```bash
python scripts/alpaca_smoke_test.py
```

This smoke test is read-only. It authenticates, reads account state, and reads positions. It does not submit an order.

## OpenAI

Configure:

- `OPENAI_API_KEY`

Then run:

```bash
python scripts/openai_smoke_test.py
```

The production adapter uses:
- OpenAI Responses API for reasoning
- OpenAI Embeddings API for semantic retrieval

CATS authority rules remain outside the model adapter. Model output must still pass CATS structured-contract and deterministic validation boundaries.

## First Real End-to-End Run

Only after PostgreSQL, Alpaca PAPER, and the model/embedding provider pass readiness checks should the system proceed to a real paper-trading end-to-end run.
