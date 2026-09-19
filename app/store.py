from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings

DATA = Path(__file__).resolve().parents[1] / "data"


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    site: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32))
    sla_minutes: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")


class WorkOrder(Base):
    __tablename__ = "work_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_by: Mapped[str | None] = mapped_column(String(80), nullable=True, default=None)
    cancelled_by: Mapped[str | None] = mapped_column(String(80), nullable=True, default=None)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    operator: Mapped[str] = mapped_column(String(80))
    session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    query: Mapped[str] = mapped_column(Text)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    risk: Mapped[str] = mapped_column(String(32), default="low")
    provider: Mapped[str] = mapped_column(String(32), default="stub")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    answer_preview: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


def _engine():
    url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


ENGINE = _engine()
SessionLocal = sessionmaker(ENGINE, expire_on_commit=False)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _work_order_public(order: WorkOrder) -> dict:
    return {
        "work_order_id": order.id,
        "device_id": order.device_id,
        "title": order.title,
        "severity": order.severity,
        "status": order.status,
        "created_at": _iso(order.created_at),
    }


def _migrate() -> None:
    statements = (
        "ALTER TABLE work_orders ADD COLUMN confirmed_by VARCHAR(80)",
        "ALTER TABLE work_orders ADD COLUMN cancelled_by VARCHAR(80)",
    )
    with ENGINE.connect() as conn:
        for stmt in statements:
            trans = conn.begin()
            try:
                conn.execute(text(stmt))
                trans.commit()
            except Exception as exc:
                trans.rollback()
                msg = str(exc).lower()
                if "already exists" in msg or "duplicate column" in msg:
                    continue
                raise


def init_db() -> None:
    Base.metadata.create_all(ENGINE)
    _migrate()
    with SessionLocal() as session:
        if session.scalar(select(Device.id).limit(1)):
            return
        rows = json.loads((DATA / "devices.json").read_text(encoding="utf-8"))
        for row in rows:
            session.add(Device(**row))
        session.commit()


def lookup_device(device_id: str) -> dict | None:
    with SessionLocal() as session:
        device = session.get(Device, device_id.upper())
        if not device:
            return None
        return {
            "id": device.id,
            "name": device.name,
            "site": device.site,
            "status": device.status,
            "sla_minutes": device.sla_minutes,
            "notes": device.notes,
        }


def create_work_order(
    device_id: str,
    title: str,
    severity: str = "medium",
    *,
    require_confirm: bool = False,
) -> dict:
    with SessionLocal() as session:
        order = WorkOrder(
            device_id=device_id.upper(),
            title=title,
            severity=severity,
            status="pending_confirm" if require_confirm else "open",
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return {
            "work_order_id": order.id,
            "device_id": order.device_id,
            "title": order.title,
            "severity": order.severity,
            "status": order.status,
        }


def get_work_order(work_order_id: int) -> dict | None:
    with SessionLocal() as session:
        order = session.get(WorkOrder, work_order_id)
        if not order:
            return None
        return _work_order_public(order)


def list_work_orders(status: str | None = None, limit: int = 50) -> list[dict]:
    with SessionLocal() as session:
        stmt = select(WorkOrder)
        if status is not None:
            stmt = stmt.where(WorkOrder.status == status)
        stmt = stmt.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc()).limit(limit)
        return [_work_order_public(order) for order in session.scalars(stmt)]


def confirm_work_order(work_order_id: int, operator: str = "intern") -> dict | None:
    with SessionLocal() as session:
        order = session.get(WorkOrder, work_order_id)
        if not order:
            return None
        if order.status == "pending_confirm":
            order.status = "open"
            order.confirmed_by = operator
            session.commit()
            session.refresh(order)
        return _work_order_public(order)


def cancel_work_order(work_order_id: int, operator: str = "intern") -> dict | None:
    with SessionLocal() as session:
        order = session.get(WorkOrder, work_order_id)
        if not order:
            return None
        if order.status in ("pending_confirm", "open"):
            order.status = "cancelled"
            order.cancelled_by = operator
            session.commit()
            session.refresh(order)
        return _work_order_public(order)


def sla_for(device_id: str) -> dict | None:
    device = lookup_device(device_id)
    if not device:
        return None
    return {
        "device_id": device["id"],
        "sla_minutes": device["sla_minutes"],
        "priority": "P1" if device["sla_minutes"] <= 30 else "P2" if device["sla_minutes"] <= 120 else "P3",
    }


def record_audit(
    *,
    query: str,
    operator: str = "intern",
    session_id: str | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
    risk: str = "low",
    provider: str = "stub",
    latency_ms: int = 0,
    answer: str = "",
    citations: list | None = None,
    actions: list | None = None,
) -> int:
    payload = json.dumps(
        {"citations": citations or [], "actions": actions or []},
        default=str,
    )
    with SessionLocal() as session:
        event = AuditEvent(
            operator=operator,
            session_id=session_id,
            query=query,
            blocked=blocked,
            block_reason=block_reason,
            risk=risk,
            provider=provider,
            latency_ms=latency_ms,
            answer_preview=(answer or "")[:500],
            payload_json=payload,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event.id


def count_audit() -> int:
    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(AuditEvent)) or 0)


def list_audit(limit: int = 50) -> list[dict]:
    with SessionLocal() as session:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)
        rows = []
        for event in session.scalars(stmt):
            rows.append(
                {
                    "id": event.id,
                    "created_at": _iso(event.created_at),
                    "operator": event.operator,
                    "session_id": event.session_id,
                    "query": event.query,
                    "blocked": bool(event.blocked),
                    "block_reason": event.block_reason,
                    "risk": event.risk,
                    "provider": event.provider,
                    "latency_ms": event.latency_ms,
                    "answer_preview": event.answer_preview,
                    "payload_json": event.payload_json,
                }
            )
        return rows
