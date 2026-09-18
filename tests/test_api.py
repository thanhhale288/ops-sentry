from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_ask_endpoint_returns_schema() -> None:
    res = client.post("/v1/ask", json={"query": "What is P1 according to triage?", "operator": "test"})
    assert res.status_code == 200
    body = res.json()
    assert "answer" in body
    assert "citations" in body
    assert body["blocked"] is False


def test_demo_page() -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "Ops Sentry" in res.text
