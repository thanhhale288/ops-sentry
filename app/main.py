from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.agent.loop import run_agent
from app.cache import get_cached, put_cached
from app.metrics import record, snapshot
from app.rag.retrieve import ingest
from app.schemas import AskRequest, AskResponse
from app.store import init_db

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    ingest()
    yield


app = FastAPI(
    title="Ops Sentry",
    description="Grounded internal-ops agent: RAG + typed tools + evals + injection defenses.",
    version="1.0.0",
    lifespan=lifespan,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "metrics": snapshot()}


@app.get("/v1/metrics")
def metrics() -> dict:
    return snapshot()


@app.post("/v1/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    cached = get_cached(req.query)
    if cached:
        record(cached)
        return cached
    response = run_agent(req.query)
    put_cached(req.query, response)
    record(response)
    return response
