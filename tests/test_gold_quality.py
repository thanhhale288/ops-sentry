from __future__ import annotations

import json
import re
from pathlib import Path

from app.agent.loop import run_agent
from app.rag.retrieve import retrieve

ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT / "data" / "goldset.json").read_text(encoding="utf-8"))
SOP_DIR = ROOT / "data" / "sops"
REQUIRED_KEYS = {"id", "query", "expect_doc_ids", "expect_substrings", "must_not_block"}
LOCKED_IDS = {
    "cam-flicker",
    "hvac-p1",
    "sla-acs",
    "charger",
    "robot-fire",
    "anpr-export",
    "ticket-hvac",
    "vn-access",
    "hvac-filter",
    "robot-dock",
    "acs-cctv",
    "triage-p1",
    "ocpp-timeout",
    "escalate-p2",
}
# Long enough that operator questions stay, short SOP sentences in older gold still pass.
COPY_NGRAM = 12


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold().strip()


def _sop_blobs() -> list[str]:
    return [_norm(path.read_text(encoding="utf-8")) for path in sorted(SOP_DIR.glob("*.md"))]


def _contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def test_gold_count_is_quality_sized() -> None:
    assert 14 <= len(GOLD) <= 22


def test_locked_gold_ids_remain() -> None:
    ids = {item["id"] for item in GOLD}
    assert LOCKED_IDS <= ids


def test_gold_schema_matches_existing() -> None:
    for item in GOLD:
        assert REQUIRED_KEYS <= set(item)
        assert isinstance(item["id"], str) and item["id"]
        assert isinstance(item["query"], str) and item["query"].strip()
        assert isinstance(item["expect_doc_ids"], list) and item["expect_doc_ids"]
        assert isinstance(item["expect_substrings"], list) and item["expect_substrings"]
        assert isinstance(item["must_not_block"], bool)


def test_gold_queries_are_not_sop_copies() -> None:
    blobs = _sop_blobs()
    assert blobs
    for item in GOLD:
        query = _norm(item["query"]).rstrip("?.!")
        assert query
        for blob in blobs:
            assert query not in blob
        words = re.findall(r"[a-z0-9]+(?:['’-][a-z0-9]+)?", query)
        for n in range(COPY_NGRAM, len(words) + 1):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i : i + n])
                assert all(ngram not in blob for blob in blobs), item["id"]


def test_gold_retrieve_and_stub_answer() -> None:
    for item in GOLD:
        hits = retrieve(item["query"])
        doc_ids = {h["doc_id"] for h in hits}
        retrieved = any(doc in doc_ids for doc in item["expect_doc_ids"])
        response = run_agent(item["query"])
        blob = json.dumps(response.model_dump(), ensure_ascii=False)
        answered = all(_contains(blob, s) for s in item["expect_substrings"])
        not_blocked_ok = (not response.blocked) == item.get("must_not_block", True)
        assert retrieved, item["id"]
        assert answered and not_blocked_ok, item["id"]
