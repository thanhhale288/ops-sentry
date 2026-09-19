from app.store import (
    cancel_work_order,
    confirm_work_order,
    create_work_order,
    get_work_order,
    list_audit,
    list_work_orders,
    lookup_device,
    record_audit,
    sla_for,
)


def test_create_work_order_default_is_open() -> None:
    result = create_work_order("ACS-11", "default open ticket")
    assert result["status"] == "open"
    assert result["device_id"] == "ACS-11"
    assert result["title"] == "default open ticket"
    assert result["severity"] == "medium"
    assert set(result) == {"work_order_id", "device_id", "title", "severity", "status"}


def test_require_confirm_confirm_and_cancel() -> None:
    pending = create_work_order("ACS-11", "needs confirm", require_confirm=True)
    assert pending["status"] == "pending_confirm"
    wo_id = pending["work_order_id"]

    fetched = get_work_order(wo_id)
    assert fetched is not None
    assert fetched["status"] == "pending_confirm"
    assert fetched["device_id"] == "ACS-11"
    assert isinstance(fetched["created_at"], str)
    assert fetched["created_at"]

    confirmed = confirm_work_order(wo_id)
    assert confirmed is not None
    assert confirmed["status"] == "open"
    again = confirm_work_order(wo_id)
    assert again is not None
    assert again["status"] == "open"
    assert again["work_order_id"] == wo_id

    cancelled = cancel_work_order(wo_id)
    assert cancelled is not None
    assert cancelled["status"] == "cancelled"

    other = create_work_order("ACS-11", "cancel pending", require_confirm=True)
    cancelled_pending = cancel_work_order(other["work_order_id"])
    assert cancelled_pending is not None
    assert cancelled_pending["status"] == "cancelled"

    assert confirm_work_order(9_999_999) is None
    assert cancel_work_order(9_999_999) is None
    assert get_work_order(9_999_999) is None


def test_list_work_orders_filters_by_status() -> None:
    pending = create_work_order("ACS-11", "list pending", require_confirm=True)
    opened = create_work_order("ACS-11", "list open")
    pending_ids = {row["work_order_id"] for row in list_work_orders(status="pending_confirm")}
    open_ids = {row["work_order_id"] for row in list_work_orders(status="open")}
    assert pending["work_order_id"] in pending_ids
    assert opened["work_order_id"] not in pending_ids
    assert opened["work_order_id"] in open_ids
    assert pending["work_order_id"] not in open_ids

    newest = list_work_orders(limit=1)
    assert len(newest) == 1
    assert newest[0]["work_order_id"] == opened["work_order_id"]
    assert isinstance(newest[0]["created_at"], str)


def test_record_audit_and_list_audit_roundtrip() -> None:
    audit_id = record_audit(
        query="unique-audit-query-acs-11",
        operator="intern",
        session_id="sess-1",
        blocked=False,
        risk="low",
        provider="stub",
        latency_ms=12,
        answer="A" * 600,
        citations=[{"doc_id": "sop-access"}],
        actions=[{"name": "lookup_device"}],
    )
    assert isinstance(audit_id, int)
    rows = list_audit(limit=50)
    assert rows
    assert rows[0]["id"] == audit_id
    match = next(row for row in rows if row["id"] == audit_id)
    assert match["query"] == "unique-audit-query-acs-11"
    assert match["operator"] == "intern"
    assert match["session_id"] == "sess-1"
    assert match["blocked"] is False
    assert match["risk"] == "low"
    assert match["provider"] == "stub"
    assert match["latency_ms"] == 12
    assert len(match["answer_preview"]) == 500
    assert "sop-access" in match["payload_json"]
    assert "lookup_device" in match["payload_json"]
    assert isinstance(match["created_at"], str)


def test_lookup_device_and_sla_for_acs_11() -> None:
    device = lookup_device("ACS-11")
    assert device is not None
    assert device["id"] == "ACS-11"
    assert device["sla_minutes"] == 10
    sla = sla_for("ACS-11")
    assert sla is not None
    assert sla["priority"] == "P1"
    assert sla["sla_minutes"] == 10
