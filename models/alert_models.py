
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(30))
    target_id: Mapped[Optional[str]] = mapped_column(String(36))
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_ws: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "alert_type": self.alert_type,
            "target_type": self.target_type, "target_id": self.target_id,
            "conditions": self.conditions, "severity": self.severity,
            "enabled": self.enabled, "notify_ws": self.notify_ws,
            "notify_email": self.notify_email, "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class AlertRecord(Base):
    __tablename__ = "alert_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("alert_rules.id", ondelete="SET NULL"))
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(30))
    target_id: Mapped[Optional[str]] = mapped_column(String(36))
    target_name: Mapped[Optional[str]] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(36))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id, "rule_id": self.rule_id, "alert_type": self.alert_type,
            "target_type": self.target_type, "target_id": self.target_id,
            "target_name": self.target_name, "title": self.title, "message": self.message,
            "severity": self.severity, "snapshot": self.snapshot,
            "is_acknowledged": self.is_acknowledged, "acknowledged_by": self.acknowledged_by,
            "is_resolved": self.is_resolved,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
