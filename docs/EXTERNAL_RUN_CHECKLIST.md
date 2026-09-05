# CATS V2E — External Run Checklist

Use this checklist before the first actual Alpaca PAPER transaction.

## A. Local software

- Python 3.11+ installed
- project virtual environment created
- project dependencies installed
- Docker Desktop installed and running
- CATS Step 19 project extracted to a writable directory

## B. Environment file

Create `.env` from `.env.local.example`.

Required values:

- `CATS_ENVIRONMENT=PAPER`
- `CATS_DATABASE_URL=postgresql+psycopg://cats:cats@localhost:5432/cats_v2e`
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`
- `ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

Do not place production broker credentials in this V2E capstone profile.

## C. PostgreSQL

Start local PostgreSQL:

```bash
python scripts/bootstrap_local_postgres.py
```

## D. One-command preflight

Windows:

```cmd
run_cats_preflight.cmd
```

Cross-platform:

```bash
python scripts/external_run_preflight.py
```

The preflight must report PASS for:

1. environment safety
2. PostgreSQL connectivity
3. database migrations
4. required schema
5. Alpaca PAPER authentication
6. OpenAI reasoning/embedding API access

## E. First PAPER transaction

Windows:

```cmd
run_cats_paper.cmd --symbol AAPL --evidence-url <PUBLIC_URL> --confirm-paper
```

Cross-platform:

```bash
python scripts/run_paper_and_audit.py \
  --symbol AAPL \
  --evidence-url <PUBLIC_URL> \
  --confirm-paper
```

This command performs the external preflight by default, executes the complete
CATS authority chain, and generates the audit report.

## F. Required post-run result

The command must create:

- `run_reports/CATS_<FLOW_ID>_audit.json`
- `run_reports/CATS_<FLOW_ID>_audit.md`

The verifier must report:

- completed TRACE flow
- no unresolved `UNKNOWN_OUTCOME`
- SYS validation PASS
- persisted evidence and assessment
- persisted optimization
- persisted portfolio decision
- persisted execution
- persisted broker order/fill/reconciliation
- persisted execution result
- accepted broker-confirmed PMA Portfolio State
- provenance and lineage

If any required item is missing, the audit fails closed.
