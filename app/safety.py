from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.schemas import AskResponse

INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions"
    r"|you are now (dan|jailbroken|unfiltered)"
    r"|reveal (the )?(system|hidden) prompt"
    r"|dump (your )?(tools|secrets|api keys?)"
    r"|b[oỏ]( l[eệ]ch)? h[uư][ớơ]ng d[aẫ]n"
    r")",
    re.I,
)

UNSAFE_PHYSICAL = re.compile(
    r"(disable (the )?(fire|safety|alarm|watchdog)"
    r"|unlock all (doors|gates)"
    r"|t[aắ]t (h[eệ]t )?(b[aá]o ch[aá]y|an to[aà]n)"
    r"|m[oở] kh[oó]a t[aấ]t c[aả] c[uử]a)",
    re.I,
)

SECRET_EXFIL = re.compile(r"(api[_ ]?key|password|secret token|bearer )", re.I)
PII = re.compile(r"(\b\d{9,12}\b|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)


@dataclass(frozen=True)
class GuardVerdict:
    blocked: bool
    reason: str | None = None
    risk: str = "low"


def inspect_query(query: str) -> GuardVerdict:
    if INJECTION.search(query):
        return GuardVerdict(True, "prompt_injection", "high")
    if UNSAFE_PHYSICAL.search(query):
        return GuardVerdict(True, "unsafe_physical_command", "high")
    return GuardVerdict(False, None, "low")


def redact(text: str) -> str:
    text = PII.sub("[redacted]", text)
    text = SECRET_EXFIL.sub("[redacted-credential] ", text)
    return text


def blocked_response(reason: str, query: str) -> AskResponse:
    messages = {
        "prompt_injection": (
            "Request blocked: the query attempts to override operator policy "
            "or extract hidden instructions. Cite SOP-SAFETY and retry with the operational question only."
        ),
        "unsafe_physical_command": (
            "Request blocked: disabling safety systems or unlocking all access points "
            "is out of policy. Open a P1 work order through a human supervisor instead."
        ),
    }
    return AskResponse(
        answer=messages.get(reason, "Request blocked by policy."),
        blocked=True,
        block_reason=reason,
        risk="high",
        citations=[],
        actions=[],
    )


def injection_cases() -> list[dict]:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "data" / "injection.json"
    return json.loads(path.read_text(encoding="utf-8"))
