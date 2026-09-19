from app.agent.loop import run_agent


def test_grounded_camera_answer_cites_policy() -> None:
    response = run_agent("CAM-014 has night IR flicker. What priority and what should I check first?")
    assert not response.blocked
    assert response.actions
    blob = " ".join(c.doc_id for c in response.citations) + response.answer
    assert "sop-camera" in blob or "sop-triage" in blob or "privacy" in response.answer.lower()


def test_creates_work_order_for_chiller() -> None:
    response = run_agent("Open a P1 work order for HVAC-3 chiller trip")
    assert not response.blocked
    names = [a.name for a in response.actions]
    assert "create_work_order" in names
    assert "lookup_device" in names
    assert response.needs_confirmation
    assert response.pending_work_order_id is not None
    assert response.audit_id is not None


def test_sla_lookup_uses_inventory_tool() -> None:
    response = run_agent("What is the SLA for ACS-11?")
    assert any(a.name == "check_sla" for a in response.actions)
    dumped = str(response.model_dump())
    assert "10" in dumped


def test_medium_work_order_still_needs_confirmation() -> None:
    response = run_agent("Open a work order for CHG-04 OCPP timeout")
    assert not response.blocked
    assert response.needs_confirmation
    assert response.pending_work_order_id is not None
