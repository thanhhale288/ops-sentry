from __future__ import annotations

import json
import time
from typing import Any

from app.agent.llm import decide, estimate_cost_usd
from app.agent.tools import run_tool
from app.config import settings
from app.safety import blocked_response, inspect_query, redact
from app.schemas import AskResponse, ToolTrace


def run_agent(query: str) -> AskResponse:
    started = time.perf_counter()
    verdict = inspect_query(query)
    if verdict.blocked:
        response = blocked_response(verdict.reason or "blocked", query)
        response.latency_ms = int((time.perf_counter() - started) * 1000)
        response.provider = settings.llm_provider
        return response

    observations: list[dict[str, Any]] = []
    actions: list[ToolTrace] = []
    decision = None
    for step in range(settings.max_agent_steps):
        decision = decide(query, observations, step)
        if decision.type == "final":
            break
        if not decision.name:
            break
        result = run_tool(decision.name, decision.args)
        observations.append({"name": decision.name, "result": result})
        actions.append(
            ToolTrace(
                name=decision.name,
                args=decision.args,
                ok="error" not in result,
                summary=json.dumps(result, ensure_ascii=False)[:240],
            )
        )
    else:
        decision = decide(query, observations, settings.max_agent_steps)

    if decision is None or decision.type != "final":
        decision = decide(query, observations, settings.max_agent_steps)

    latency_ms = int((time.perf_counter() - started) * 1000)
    return AskResponse(
        answer=redact(decision.answer),
        citations=decision.citations,
        actions=actions,
        risk=decision.risk,
        blocked=False,
        latency_ms=latency_ms,
        provider="gemini" if settings.llm_provider == "gemini" and settings.gemini_api_key else "stub",
        estimated_cost_usd=estimate_cost_usd(settings.llm_provider),
    )
