from app.rag.retrieve import retrieve
from app.store import lookup_device, sla_for


def test_retrieves_camera_privacy_sop() -> None:
    hits = retrieve("CAM-014 night IR flicker privacy mask")
    docs = {h["doc_id"] for h in hits}
    assert "sop-camera" in docs or "sop-triage" in docs


def test_retrieves_hvac_p1_sop() -> None:
    hits = retrieve("HVAC-3 chiller alarm supply temperature watchdog")
    assert any(h["doc_id"] == "sop-hvac" for h in hits)


def test_device_inventory_and_sla() -> None:
    device = lookup_device("acs-11")
    assert device is not None
    assert device["sla_minutes"] == 10
    sla = sla_for("ACS-11")
    assert sla is not None
    assert sla["priority"] == "P1"
