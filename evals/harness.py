from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.loop import run_agent
from app.rag.retrieve import ingest, retrieve
from app.store import init_db

GOLD = json.loads((ROOT / "data" / "goldset.json").read_text(encoding="utf-8"))
INJECTION = json.loads((ROOT / "data" / "injection.json").read_text(encoding="utf-8"))


def _contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def evaluate() -> dict:
    init_db()
    ingest()
    retrieval_hits = 0
    answer_hits = 0
    latencies: list[int] = []
    cases = []

    for item in GOLD:
        hits = retrieve(item["query"])
        doc_ids = {h["doc_id"] for h in hits}
        retrieved = any(doc in doc_ids for doc in item["expect_doc_ids"])
        retrieval_hits += int(retrieved)
        response = run_agent(item["query"])
        latencies.append(response.latency_ms)
        blob = json.dumps(response.model_dump(), ensure_ascii=False)
        answered = all(_contains(blob, s) for s in item["expect_substrings"])
        answer_hits += int(answered and (not response.blocked) == item.get("must_not_block", True))
        cases.append(
            {
                "id": item["id"],
                "retrieved": retrieved,
                "answered": answered,
                "blocked": response.blocked,
                "latency_ms": response.latency_ms,
                "citations": [c.doc_id for c in response.citations],
            }
        )

    injection_blocked = 0
    injection_cases = []
    for item in INJECTION:
        response = run_agent(item["query"])
        ok = response.blocked
        injection_blocked += int(ok)
        injection_cases.append({"id": item["id"], "blocked": response.blocked, "reason": response.block_reason})

    n = len(GOLD)
    m = len(INJECTION)
    p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
    scorecard = {
        "retrieval_recall": round(retrieval_hits / n, 3) if n else 0,
        "answer_pass_rate": round(answer_hits / n, 3) if n else 0,
        "injection_block_rate": round(injection_blocked / m, 3) if m else 0,
        "latency_ms_p95": p95,
        "n_gold": n,
        "n_injection": m,
        "cases": cases,
        "injection": injection_cases,
    }
    out = ROOT / "evals" / "last-scorecard.json"
    out.write_text(json.dumps(scorecard, indent=2, ensure_ascii=False), encoding="utf-8")
    return scorecard


if __name__ == "__main__":
    card = evaluate()
    print(json.dumps({k: card[k] for k in card if k not in {"cases", "injection"}}, indent=2))
    print("wrote evals/last-scorecard.json")
