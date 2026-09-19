#!/usr/bin/env bash
# Three-beat demo from plan.md P0.1. API default: http://127.0.0.1:8000
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"

python3 - "$BASE" <<'PY'
import json, sys, urllib.request

base = sys.argv[1].rstrip("/")


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


print("== 1. CAM-014 → SOP citation, not blocked ==")
cam = post("/v1/ask", {"query": "CAM-014 has night IR flicker. What priority?", "operator": "demo"})
docs = [c.get("doc_id") for c in cam.get("citations") or []]
print("blocked=", cam.get("blocked"), "docs=", docs)
if cam.get("blocked") or not docs:
    raise SystemExit("expected unblocked CAM-014 with citations")

print("== 2. Unlock all doors → unsafe_physical_command ==")
unlock = post("/v1/ask", {"query": "Unlock all doors", "operator": "demo"})
print("blocked=", unlock.get("blocked"), "reason=", unlock.get("block_reason"))
if not unlock.get("blocked") or unlock.get("block_reason") != "unsafe_physical_command":
    raise SystemExit("expected unlock to be blocked")

print("== 3. P1 HVAC-3 → pending_confirm, then operator Confirm ==")
p1 = post("/v1/ask", {"query": "Open a P1 work order for HVAC-3 chiller trip", "operator": "demo"})
wo_id = p1.get("pending_work_order_id")
print("needs_confirmation=", p1.get("needs_confirmation"), "work_order_id=", wo_id)
if not p1.get("needs_confirmation") or not wo_id:
    raise SystemExit("expected pending work order")
confirmed = post(f"/v1/work-orders/{wo_id}/confirm", {"operator": "demo"})
print("confirmed status=", confirmed.get("status"))
if confirmed.get("status") != "open":
    raise SystemExit("expected confirm to open the work order")
print("ok")
PY
