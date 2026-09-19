from __future__ import annotations

import time
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.agent.loop import _write_audit, run_agent
from app.auth import require_ops_token
from app.cache import get_cached, put_cached
from app.metrics import record, snapshot
from app.rag.retrieve import ingest
from app.safety import denylist_version
from app.schemas import AskRequest, AskResponse, OperatorAction
from app.store import (
    cancel_work_order,
    confirm_work_order,
    get_work_order,
    init_db,
    list_audit,
    list_work_orders,
)


def _boot(attempts: int = 10) -> None:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            init_db()
            ingest()
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(min(attempt, 3))
    raise last_exc or RuntimeError("startup failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _boot()
    yield


app = FastAPI(
    title="Ops Sentry",
    description="Grounded internal-ops agent: RAG + typed tools + evals + injection defenses.",
    version="1.1.0",
    lifespan=lifespan,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"
Auth = Depends(require_ops_token)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "denylist_version": denylist_version(), "metrics": snapshot()}


@app.get("/v1/metrics", dependencies=[Auth])
def metrics() -> dict:
    return snapshot()


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Auth])
def ask(req: AskRequest) -> AskResponse:
    cached = get_cached(req.query)
    if cached:
        _write_audit(req.query, req.operator, req.session_id, cached)
        record(cached)
        return cached
    response = run_agent(req.query, operator=req.operator, session_id=req.session_id)
    put_cached(req.query, response)
    record(response)
    return response


@app.get("/v1/work-orders", dependencies=[Auth])
def work_orders(status: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {"work_orders": list_work_orders(status=status, limit=limit)}


@app.post("/v1/work-orders/{work_order_id}/confirm", dependencies=[Auth])
def confirm_order(work_order_id: int, body: OperatorAction) -> dict:
    current = get_work_order(work_order_id)
    if current is None:
        raise HTTPException(status_code=404, detail="work_order_not_found")
    if current["status"] == "cancelled":
        raise HTTPException(status_code=409, detail="work_order_cancelled")
    result = confirm_work_order(work_order_id, operator=body.operator)
    if result is None:
        raise HTTPException(status_code=404, detail="work_order_not_found")
    return result


@app.post("/v1/work-orders/{work_order_id}/cancel", dependencies=[Auth])
def cancel_order(work_order_id: int, body: OperatorAction) -> dict:
    result = cancel_work_order(work_order_id, operator=body.operator)
    if result is None:
        raise HTTPException(status_code=404, detail="work_order_not_found")
    return result


@app.get("/v1/audit", dependencies=[Auth])
def audit(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {"events": list_audit(limit=limit)}


@app.post("/v1/knowledge/ingest", dependencies=[Auth])
def ingest_knowledge(force: bool = False) -> dict:
    return {"upserted": ingest(force=force)}
