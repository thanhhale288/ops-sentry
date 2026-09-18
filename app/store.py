from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
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


def _engine():
    url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


ENGINE = _engine()
SessionLocal = sessionmaker(ENGINE, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(ENGINE)
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


def create_work_order(device_id: str, title: str, severity: str = "medium") -> dict:
    with SessionLocal() as session:
        order = WorkOrder(device_id=device_id.upper(), title=title, severity=severity)
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


def sla_for(device_id: str) -> dict | None:
    device = lookup_device(device_id)
    if not device:
        return None
    return {
        "device_id": device["id"],
        "sla_minutes": device["sla_minutes"],
        "priority": "P1" if device["sla_minutes"] <= 30 else "P2" if device["sla_minutes"] <= 120 else "P3",
    }
