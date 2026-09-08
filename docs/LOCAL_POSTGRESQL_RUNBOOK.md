# CATS V2ET — Local PostgreSQL Runbook

This step converts the database from an abstract dependency into a reproducible local service.

## 1. Copy environment template

Copy `.env.local.example` to `.env` and fill only the credentials that are available.

## 2. Start PostgreSQL

```bash
python scripts/bootstrap_local_postgres.py
```

Equivalent manual command:

```bash
docker compose up -d postgres
```

## 3. Run database preflight

```bash
python scripts/local_database_preflight.py
```

This performs:

1. PostgreSQL connectivity
2. Alembic upgrade to head
3. required CATS schema verification

## 4. External API preflight

After adding Alpaca PAPER and OpenAI credentials:

```bash
python scripts/preflight_real_run.py
```

## 5. First PAPER flow

Only after all checks pass:

```bash
python scripts/first_real_paper_flow.py \
  --symbol AAPL \
  --evidence-url <PUBLIC_EVIDENCE_URL> \
  --confirm-paper
```

The execution remains PAPER-only and must traverse the full CATS authority chain.
