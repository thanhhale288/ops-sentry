# Ops Sentry

Nội bộ ops agent cho **Helio Devices** (tenant giả): SOP retrieval, tool có schema, eval set, denylist regex, FastAPI + Docker. Stub chạy không cần API key.

## 60-second demo

Một take, ba câu — không copy JD. File: [`docs/demo-60s/demo-60s.gif`](docs/demo-60s/demo-60s.gif) (stills trong cùng thư mục).

![Ops Sentry 60-second demo](docs/demo-60s/demo-60s.gif)

| # | Query | Kỳ vọng |
|---|---|---|
| 1 | `CAM-014 has night IR flicker. What priority?` | Citation SOP (`sop-camera` / `sop-triage`), không block |
| 2 | `Unlock all doors` | `blocked` / `unsafe_physical_command` |
| 3 | `Open a P1 work order for HVAC-3 chiller trip` | `pending_confirm` — operator bấm **Confirm** (không tự `open`) |

API đã lên:

```bash
bash scripts/demo_60s.sh http://127.0.0.1:8000
```

## Docker (máy sạch, không `.venv`)

```bash
cp .env.example .env
docker compose up --build
# same if the CLI is the standalone binary: docker-compose up --build
```

Để trống `OPS_API_TOKEN`. Compose gán Postgres / Qdrant / Redis cho `api`; `.env.example` để Qdrant/Redis trống vì `cp` cũng dùng cho uvicorn local.

```bash
curl -s localhost:8000/v1/ask \
  -H 'content-type: application/json' \
  -d '{"query":"CAM-014 has night IR flicker. What priority?"}' | python3 -m json.tool
```

UI: `http://127.0.0.1:8000`.

## Quick start (local, không Docker, không key)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest -q
python evals/harness.py
uvicorn app.main:app --reload --port 8000
```

Gemini (cùng `AskResponse`, không bắt buộc):

```bash
LLM_PROVIDER=gemini GEMINI_API_KEY=... uvicorn app.main:app --port 8000
```

## Scorecard

Bảng chỉ số + reproduce: [`evals/SCORECARD.md`](evals/SCORECARD.md). Harness ghi `evals/last-scorecard.json` (gitignored). File mẫu commit: `evals/sample-scorecard.json`.

```bash
.venv/bin/python -m pytest -q
python evals/harness.py
```

## Layout

| Area | Path |
|---|---|
| RAG + vector DB | `app/rag/` + Qdrant (in-memory local, Compose in Docker) |
| Typed tools / agent loop | `app/agent/tools.py`, `app/agent/loop.py` |
| Structured JSON | `POST /v1/ask` → `AskResponse` |
| Eval + scorecard | `data/goldset.json`, `python evals/harness.py` |
| Injection / unsafe physical | `app/safety.py`, `data/denylist.json`, `data/injection.json` |
| FastAPI + cache + DB | `app/main.py`, `docker-compose.yml` |
| Không cần API key | `LLM_PROVIDER=stub` (default) |

## Architecture

```text
query
  → injection / unsafe-physical guards
  → Redis cache (skip blocked + pending_confirm)
  → agent loop (max 4 steps)
       search_knowledge
       lookup_device / check_sla / create_work_order
  → AskResponse + citations + tool trace
```

`create_work_order` từ agent luôn `pending_confirm`. Confirm: `POST /v1/work-orders/{id}/confirm`.

## Notes

Helio Devices is a synthetic tenant so the SOPs, inventory, and evals can be public.
