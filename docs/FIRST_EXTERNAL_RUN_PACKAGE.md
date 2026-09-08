# CATS V2ET — First External Run Package

Construction Step 19 packages the operational path into three actions.

## 1. Start database

```bash
python scripts/bootstrap_local_postgres.py
```

## 2. Preflight

```bash
python scripts/external_run_preflight.py
```

Windows shortcut:

```cmd
run_cats_preflight.cmd
```

## 3. Run and audit

```bash
python scripts/run_paper_and_audit.py \
  --symbol AAPL \
  --evidence-url <PUBLIC_EVIDENCE_URL> \
  --confirm-paper
```

Windows shortcut:

```cmd
run_cats_paper.cmd --symbol AAPL --evidence-url <PUBLIC_EVIDENCE_URL> --confirm-paper
```

The runner performs preflight unless `--skip-preflight` is explicitly supplied.
The PAPER confirmation flag is always required.

After execution, the system automatically verifies the latest persisted flow and
writes both JSON and Markdown audit reports to `run_reports/`.
