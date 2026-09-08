# CATS V2ET — Streamlit UI Step 01

## Scope

This patch adds a **read-only capstone observability UI**. It is intentionally outside CATS decision authority.

It does not:

- call Alpaca;
- submit or cancel orders;
- invoke Qwen or another LLM;
- execute retrieval;
- modify CATS database state;
- alter PMA/PMS/SYS/TEA/TES authority.

The dashboard reads persisted PostgreSQL state and presents the complete CATS vertical slice for demonstration and inspection.

## Added files

- `src/cats/ui/read_model.py` — SELECT-only database read model.
- `src/cats/ui/__init__.py`
- `scripts/streamlit_dashboard.py` — Streamlit capstone dashboard.
- `tests/test_ui_read_model.py` — read-model tests.
- `requirements-ui.txt` — optional UI dependency.

## Initial dashboard

The first UI provides:

1. environment/database banner;
2. recent TRACE flows;
3. flow selection;
4. authority/material-flow stage cards;
5. current-vs-selected-target quantity projection;
6. raw persisted stage details;
7. recent flow history.

## Install Streamlit

```bash
python -m pip install -r requirements-ui.txt
```

## Run

The normal CATS environment must be loaded first so the dashboard can read `CATS_DATABASE_URL`.

```bash
set -a
source .env
set +a

streamlit run scripts/streamlit_dashboard.py
```

Streamlit normally opens the local dashboard in the browser and also prints its localhost URL.

## Safety boundary

The UI imports only configuration/database/read-model code. There is no broker or execution control in Step 01.
