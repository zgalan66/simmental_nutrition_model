\
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class Formula(Base):
    __tablename__ = "formulas"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[Optional[str]] = mapped_column(String(200))
    user_id: Mapped[Optional[str]] = mapped_column(String(36))
    ingredients: Mapped[dict] = mapped_column(JSON, default=dict)
    nutrition_result: Mapped[dict] = mapped_column(JSON, default=dict)
    total_cost: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FormulaVersion(Base):
    __tablename__ = "formula_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    formula_id: Mapped[str] = mapped_column(String(36), ForeignKey("formulas.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
