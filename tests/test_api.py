from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.store import create_work_order, get_work_order

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["denylist_version"]


def test_ask_endpoint_returns_schema() -> None:
    res = client.post("/v1/ask", json={"query": "What is P1 according to triage?", "operator": "test"})
    assert res.status_code == 200
    body = res.json()
    assert "answer" in body
    assert "citations" in body
    assert body["blocked"] is False
    assert body["audit_id"]


def test_demo_page() -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "Ops Sentry" in res.text
    assert 'id="ask-form"' in res.text
    assert "CAM-014 has night IR flicker. What priority?" in res.text
    assert "Unlock all doors" in res.text
    assert "Open a P1 work order for HVAC-3 chiller trip" in res.text


def test_p1_ask_requires_confirmation_then_confirm_endpoint() -> None:
    res = client.post(
        "/v1/ask",
        json={"query": "Open a P1 work order for HVAC-3 chiller trip", "operator": "test"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["needs_confirmation"] is True
    wo_id = body["pending_work_order_id"]
    assert wo_id
    listed = client.get("/v1/work-orders", params={"status": "pending_confirm"})
    assert listed.status_code == 200
    ids = {row["work_order_id"] for row in listed.json()["work_orders"]}
    assert wo_id in ids
    confirmed = client.post(f"/v1/work-orders/{wo_id}/confirm", json={"operator": "test"})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "open"


def test_cancel_work_order_endpoint() -> None:
    created = create_work_order("CAM-014", "cancel via api", severity="high", require_confirm=True)
    wo_id = created["work_order_id"]
    res = client.post(f"/v1/work-orders/{wo_id}/cancel", json={"operator": "test"})
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"
    assert get_work_order(wo_id)["status"] == "cancelled"


def test_audit_and_ingest_endpoints() -> None:
    client.post("/v1/ask", json={"query": "What is the SLA for ACS-11?", "operator": "audit-test"})
    audit = client.get("/v1/audit", params={"limit": 10})
    assert audit.status_code == 200
    events = audit.json()["events"]
    assert events
    ingest = client.post("/v1/knowledge/ingest")
    assert ingest.status_code == 200
    assert ingest.json()["upserted"] > 0


def test_auth_rejects_when_token_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPS_API_TOKEN", "secret-test-token")
    res = client.get("/v1/metrics")
    assert res.status_code == 401
    ok = client.get("/v1/metrics", headers={"X-Ops-Token": "secret-test-token"})
    assert ok.status_code == 200
    monkeypatch.delenv("OPS_API_TOKEN", raising=False)


def test_production_without_token_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("OPS_ENV", "production")
    monkeypatch.delenv("OPS_API_TOKEN", raising=False)
    res = client.get("/v1/metrics")
    assert res.status_code == 503


def test_cached_ask_still_writes_audit() -> None:
    query = "What is P1 according to triage?"
    first = client.post("/v1/ask", json={"query": query, "operator": "cache-a"})
    second = client.post("/v1/ask", json={"query": query, "operator": "cache-b"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cached"] is True
    events = client.get("/v1/audit", params={"limit": 20}).json()["events"]
    operators = {e["operator"] for e in events if e["query"] and "triage" in e["query"].lower()}
    assert "cache-b" in operators or any(e.get("operator") == "cache-b" for e in events)

