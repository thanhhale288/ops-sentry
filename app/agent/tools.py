from __future__ import annotations

from typing import Any, Callable

from app.rag.retrieve import retrieve
from app.store import create_work_order, lookup_device, sla_for

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


def _search_knowledge(args: dict[str, Any]) -> dict[str, Any]:
    hits = retrieve(str(args.get("query", "")), k=int(args.get("k", 5)))
    return {"hits": hits}


def _lookup_device(args: dict[str, Any]) -> dict[str, Any]:
    device = lookup_device(str(args.get("device_id", "")))
    return device or {"error": "device_not_found"}


def _create_work_order(args: dict[str, Any]) -> dict[str, Any]:
    return create_work_order(
        device_id=str(args.get("device_id", "")),
        title=str(args.get("title", "unspecified incident")),
        severity=str(args.get("severity", "medium")),
    )


def _check_sla(args: dict[str, Any]) -> dict[str, Any]:
    sla = sla_for(str(args.get("device_id", "")))
    return sla or {"error": "device_not_found"}


TOOLS: dict[str, ToolFn] = {
    "search_knowledge": _search_knowledge,
    "lookup_device": _lookup_device,
    "create_work_order": _create_work_order,
    "check_sla": _check_sla,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_knowledge",
        "description": "Retrieve SOP and policy chunks from the internal knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "lookup_device",
        "description": "Look up a Helio device by id (e.g. CAM-014, HVAC-3).",
        "parameters": {
            "type": "object",
            "properties": {"device_id": {"type": "string"}},
            "required": ["device_id"],
        },
    },
    {
        "name": "check_sla",
        "description": "Return the response SLA and priority for a device.",
        "parameters": {
            "type": "object",
            "properties": {"device_id": {"type": "string"}},
            "required": ["device_id"],
        },
    },
    {
        "name": "create_work_order",
        "description": "Open a work order. Never use this to disable safety systems.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "title": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["device_id", "title"],
        },
    },
]


def run_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"error": "unknown_tool"}
    return TOOLS[name](args)
