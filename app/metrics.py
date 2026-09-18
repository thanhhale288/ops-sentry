from __future__ import annotations

from collections import deque

from app.schemas import AskResponse

_latencies: deque[int] = deque(maxlen=200)
_total = 0
_blocked = 0
_cached = 0
_cost = 0.0


def record(response: AskResponse) -> None:
    global _total, _blocked, _cached, _cost
    _total += 1
    _latencies.append(response.latency_ms)
    _cost += response.estimated_cost_usd
    if response.blocked:
        _blocked += 1
    if response.cached:
        _cached += 1


def snapshot() -> dict:
    values = sorted(_latencies)
    p95 = values[int(0.95 * (len(values) - 1))] if values else 0
    avg = int(sum(values) / len(values)) if values else 0
    return {
        "requests": _total,
        "blocked": _blocked,
        "cache_hits": _cached,
        "block_rate": round(_blocked / _total, 3) if _total else 0.0,
        "cache_hit_rate": round(_cached / _total, 3) if _total else 0.0,
        "latency_ms_avg": avg,
        "latency_ms_p95": p95,
        "estimated_cost_usd": round(_cost, 6),
    }
