# Ops Sentry

Ops Sentry is a FastAPI ops agent for fictional Helio Devices: SOP retrieval, schema-typed tools, evals, and regex denylist guards.

## Tests

- `.venv/bin/python -m pytest -q`
- `python evals/harness.py`

## Layout

- `app/main.py` — FastAPI (`POST /v1/ask`, work-order HITL)
- `app/agent/loop.py` — agent loop
- `app/agent/llm.py` — stub (default) or Gemini
- `app/agent/tools.py` — `search_knowledge`, `lookup_device`, `check_sla`, `create_work_order`
- `app/safety.py` — versioned denylist regex, not a classifier
- `app/store.py` — devices / work orders
- `app/rag/retrieve.py` — hybrid SOP retrieval (hash dense + BM25 RRF)
- `app/rag/bm25.py` — in-process BM25 index
- `app/cache.py` — response cache
- `app/auth.py` — `OPS_API_TOKEN` gate
- `templates/index.html` — demo UI
- `data/sops/` — SOP corpus
- `data/goldset.json` — eval gold set
- `data/denylist.json` — injection + unsafe-physical patterns

## Runtime

- Stub is default (`LLM_PROVIDER=stub`). Gemini is optional (`LLM_PROVIDER=gemini` + `GEMINI_API_KEY`).
- HITL: `create_work_order` from tools is `pending_confirm`. Confirm via `POST /v1/work-orders/{id}/confirm`.
- Auth: empty `OPS_API_TOKEN` = open demo; set a token in production.
- `.env` is gitignored. Do not commit secrets.

## Constraints

- Do not add LangChain/LangGraph.
- Prefer existing modules over new frameworks.
