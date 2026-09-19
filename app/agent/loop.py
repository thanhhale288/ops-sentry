from __future__ import annotations

import json
import time
from typing import Any

from app.agent.llm import decide, estimate_cost_usd
from app.agent.tools import run_tool
from app.config import settings
from app.safety import blocked_response, inspect_query, redact
from app.schemas import AskResponse, ToolTrace
from app.store import record_audit


def _write_audit(query: str, operator: str, session_id: str | None, response: AskResponse) -> None:
    try:
        response.audit_id = record_audit(
            query=redact(query),
            operator=operator,
            session_id=session_id,
            blocked=response.blocked,
            block_reason=response.block_reason,
            risk=response.risk,
            provider=response.provider,
            latency_ms=response.latency_ms,
            answer=response.answer,
            citations=[c.model_dump() for c in response.citations],
            actions=[a.model_dump() for a in response.actions],
        )
    except Exception:
        return


def run_agent(query: str, operator: str = "intern", session_id: str | None = None) -> AskResponse:
    started = time.perf_counter()
    verdict = inspect_query(query)
    if verdict.blocked:
        response = blocked_response(verdict.reason or "blocked", query)
        response.latency_ms = int((time.perf_counter() - started) * 1000)
        response.provider = settings.llm_provider
        _write_audit(query, operator, session_id, response)
        return response

    observations: list[dict[str, Any]] = []
    actions: list[ToolTrace] = []
    pending_id: int | None = None
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
        if decision.name == "create_work_order" and result.get("status") == "pending_confirm":
            try:
                pending_id = int(result["work_order_id"])
            except (KeyError, TypeError, ValueError):
                pass
    else:
        decision = decide(query, observations, settings.max_agent_steps)

    if decision is None or decision.type != "final":
        decision = decide(query, observations, settings.max_agent_steps)

    latency_ms = int((time.perf_counter() - started) * 1000)
    risk = "high" if pending_id is not None else decision.risk
    response = AskResponse(
        answer=redact(decision.answer),
        citations=decision.citations,
        actions=actions,
        risk=risk,
        blocked=False,
        latency_ms=latency_ms,
        provider="gemini" if settings.llm_provider == "gemini" and settings.gemini_api_key else "stub",
        estimated_cost_usd=estimate_cost_usd(settings.llm_provider),
        needs_confirmation=pending_id is not None,
        pending_work_order_id=pending_id,
    )
    _write_audit(query, operator, session_id, response)
    return response
