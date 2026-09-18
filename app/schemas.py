from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Risk = Literal["low", "medium", "high"]


class Citation(BaseModel):
    doc_id: str
    title: str
    quote: str


class ToolTrace(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    summary: str = ""


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    operator: str = "intern"
    session_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    actions: list[ToolTrace] = Field(default_factory=list)
    risk: Risk = "low"
    blocked: bool = False
    block_reason: str | None = None
    cached: bool = False
    latency_ms: int = 0
    provider: str = "stub"
    estimated_cost_usd: float = 0.0


class LlmDecision(BaseModel):
    type: Literal["tool", "final"]
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    answer: str = ""
    citations: list[Citation] = Field(default_factory=list)
    risk: Risk = "low"
