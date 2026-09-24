from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas import AskResponse

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DENYLIST_PATH = _DATA_DIR / "denylist.json"

# Used when denylist.json is missing so inspect_query never crashes at import.
# Keep in sync with data/denylist.json so a clone without that file still
# blocks P0.5 paraphrases (e.g. "Unlock all the doors") and not gold vn-access.
_FALLBACK_INJECTION = [
    r"(ignore|forget|override) (all |any |the |your )?(previous |prior |above )?(instructions|rules)",
    r"disregard (the |all |any )?(previous |prior |above )?(instructions|rules)",
    r"you are (now )?(dan|jailbroken|unfiltered)( now)?\b",
    r"(reveal|print|show|dump) (me )?(the |your )?(system|hidden) prompt",
    r"dump (your )?(tools|secrets|api keys?)",
    r"(no|without)( a)? safety policy",
    r"b[oỏ]( l[eệ]ch| qua.{0,40}| h[eế]t| t[aấ]t c[aả])? h[uư][ớơ]ng d[aẫ]n",
    r"qu[eê]n.{0,40}h[uư][ớơ]ng d[aẫ]n",
    r"b[oỏ] qua (các |mọi )?(quy t[aắ]c|policy)",
    r"(đừng|kh[oô]ng) tu[aâ]n theo.{0,40}h[uư][ớơ]ng d[aẫ]n",
    r"(?:đ[oó]ng vai|b[aạ]n là) dan\b",
]
_FALLBACK_UNSAFE_PHYSICAL = [
    r"disable (the |all |all the )?(fire|safety|alarm|watchdog)",
    r"(turn|switch|shut) off (the |all |all the )?(fire|safety|alarm|watchdog)",
    r"unlock (all|every) (?:the |of the |of our |our |single )?(doors?|gates?)",
    r"open (every|all) (?:the |of the |of our |our |single )?(doors?|gates?)",
    r"t[aắ]t.{0,40}(b[aá]o ch[aá]y|an to[aà]n)",
    r"m[oở] kh(?:[oó]a|oá) (?:t[aấ]t c[aả]|h[eế]t|m[oọ]i|to[aà]n b[oộ]) (?:c[aá]c )?(?:c[uử]a|c[oổ]ng)",
    r"v[oô] hi[eệ]u h[oó][aá].{0,40}(b[aá]o ch[aá]y|an to[aà]n)",
]

_REGEX_CACHE: dict[str, re.Pattern[str]] = {}


def _compile_patterns(patterns: list[str]) -> re.Pattern[str]:
    cleaned = [p for p in patterns if p]
    if not cleaned:
        return re.compile(r"(?!)")
    return re.compile("|".join(f"(?:{p})" for p in cleaned), re.I)


def _read_denylist() -> tuple[str, list[str], list[str]]:
    try:
        raw = json.loads(_DENYLIST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return "", list(_FALLBACK_INJECTION), list(_FALLBACK_UNSAFE_PHYSICAL)
    if not isinstance(raw, dict):
        return "", list(_FALLBACK_INJECTION), list(_FALLBACK_UNSAFE_PHYSICAL)

    version = str(raw.get("version") or "")
    injection = raw.get("injection_patterns")
    unsafe = raw.get("unsafe_physical_patterns")
    if not isinstance(injection, list) or not injection:
        injection = list(_FALLBACK_INJECTION)
    if not isinstance(unsafe, list) or not unsafe:
        unsafe = list(_FALLBACK_UNSAFE_PHYSICAL)
    injection_patterns = [p for p in injection if isinstance(p, str) and p]
    unsafe_patterns = [p for p in unsafe if isinstance(p, str) and p]
    if not injection_patterns:
        injection_patterns = list(_FALLBACK_INJECTION)
    if not unsafe_patterns:
        unsafe_patterns = list(_FALLBACK_UNSAFE_PHYSICAL)
    return version, injection_patterns, unsafe_patterns


def _cached_compile(name: str, patterns: list[str]) -> re.Pattern[str]:
    compiled = _REGEX_CACHE.get(name)
    if compiled is None:
        compiled = _compile_patterns(patterns)
        _REGEX_CACHE[name] = compiled
    return compiled


_DENYLIST_VERSION, _injection_patterns, _unsafe_patterns = _read_denylist()
INJECTION = _cached_compile("injection", _injection_patterns)
UNSAFE_PHYSICAL = _cached_compile("unsafe_physical", _unsafe_patterns)

SECRET_EXFIL = re.compile(r"(api[_ ]?key|password|secret token|bearer )", re.I)
PII = re.compile(r"(\b\d{9,12}\b|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)


@dataclass(frozen=True)
class GuardVerdict:
    blocked: bool
    reason: str | None = None
    risk: str = "low"


def denylist_version() -> str:
    return _DENYLIST_VERSION


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
    path = _DATA_DIR / "injection.json"
    return json.loads(path.read_text(encoding="utf-8"))
