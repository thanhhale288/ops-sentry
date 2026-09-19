import pytest

from app.agent.llm import GeminiBlocked, _decision_from_gemini


def test_gemini_function_call_maps_to_tool_decision() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"functionCall": {"name": "lookup_device", "args": {"device_id": "ACS-11"}}}
                    ]
                }
            }
        ]
    }
    decision = _decision_from_gemini(payload)
    assert decision.type == "tool"
    assert decision.name == "lookup_device"
    assert decision.args["device_id"] == "ACS-11"


def test_gemini_text_falls_back_to_final_answer() -> None:
    payload = {"candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]}
    decision = _decision_from_gemini(payload)
    assert decision.type == "final"
    assert "not json" in decision.answer


def test_gemini_safety_finish_raises_blocked() -> None:
    with pytest.raises(GeminiBlocked):
        _decision_from_gemini({"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]})
