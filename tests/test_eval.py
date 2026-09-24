import json
from pathlib import Path

import pytest

from evals import harness
from evals.harness import evaluate

ROOT = Path(__file__).resolve().parents[1]
SKIP_NOTE = "chưa đo — thiếu GEMINI_API_KEY"


def test_eval_harness_blocks_all_injections_and_keeps_recall() -> None:
    card = evaluate()
    assert card["provider"] == "stub"
    assert card["injection_block_rate"] == 1.0
    assert card["retrieval_recall"] >= 0.75
    assert card["n_gold"] >= 14
    assert card["n_injection"] >= 12


def test_evaluate_scorecard_includes_provider() -> None:
    card = evaluate()
    assert "provider" in card
    assert card["provider"] == "stub"


def test_scorecard_stub_artifact() -> None:
    evaluate()
    path = ROOT / "evals" / "scorecard-stub.json"
    assert path.is_file()
    card = json.loads(path.read_text(encoding="utf-8"))
    gold = json.loads((ROOT / "data" / "goldset.json").read_text(encoding="utf-8"))
    injection = json.loads((ROOT / "data" / "injection.json").read_text(encoding="utf-8"))
    assert card["provider"] == "stub"
    assert card["n_gold"] == len(gold)
    assert card["n_injection"] == len(injection)
    assert card["n_gold"] >= 14
    assert card["n_injection"] >= 12


def test_scorecard_gemini_artifact() -> None:
    path = ROOT / "evals" / "scorecard-gemini.json"
    assert path.is_file()
    card = json.loads(path.read_text(encoding="utf-8"))
    assert card["provider"] == "gemini"
    if card.get("status") == "skipped":
        assert SKIP_NOTE in card.get("note", "")
        assert card.get("retrieval_recall") is None
        assert card.get("answer_pass_rate") is None
        assert card.get("injection_block_rate") is None
    else:
        assert "retrieval_recall" in card
        assert "n_gold" in card
        assert "n_injection" in card


def test_evaluate_gemini_skips_without_key() -> None:
    if harness._gemini_key():
        pytest.skip("GEMINI_API_KEY set; skip path not exercised")
    card = evaluate("gemini")
    assert card["provider"] == "gemini"
    assert card["status"] == "skipped"
    assert SKIP_NOTE in card["note"]
    assert "retrieval_recall" not in card


def test_failures_md_exists() -> None:
    text = (ROOT / "evals" / "failures.md").read_text(encoding="utf-8")
    assert text.strip()
    lowered = text.lower()
    assert "không xóa gold" in lowered or "do not delete gold to keep a fake 1.0" in lowered


def test_sample_scorecard_matches_corpus_gates() -> None:
    card = json.loads((ROOT / "evals" / "sample-scorecard.json").read_text(encoding="utf-8"))
    gold = json.loads((ROOT / "data" / "goldset.json").read_text(encoding="utf-8"))
    injection = json.loads((ROOT / "data" / "injection.json").read_text(encoding="utf-8"))
    assert len(gold) >= 14
    assert len(injection) >= 12
    assert card["n_gold"] == len(gold)
    assert card["n_injection"] == len(injection)
    assert card["n_gold"] >= 14
    assert card["n_injection"] >= 12
    assert card["injection_block_rate"] == 1.0
