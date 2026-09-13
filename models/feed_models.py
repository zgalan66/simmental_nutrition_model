"""
models/feed_models.py — 原料模型（完整版，双模型共用）
覆盖 scaffold 生成的占位版，字段与 nutrition_engine / optimize_engine 对齐
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


def parse_mid(value):
    """
    把营养数据统一成 float：
    - '13.0~13.4' / '13.0～13.4' → 取中位数 13.2
    - 纯数字字符串 → float
    - 空 / nan / None → None
    """
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "nan", "None", "-", "—"):
        return None
    for sep in ["~", "～"]:
        if sep in s:
            try:
                nums = [float(p.strip()) for p in s.split(sep) if p.strip() != ""]
                if nums:
                    return round(sum(nums) / len(nums), 4)
            except ValueError:
                break
    try:
        return round(float(s), 4)
    except ValueError:
        return None


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))

    # —— 核心营养指标（与 NUTRIENT_FIELDS 对齐）——
    cp_pct: Mapped[Optional[float]] = mapped_column(Float)      # 粗蛋白 CP（%DM）
    ndf_pct: Mapped[Optional[float]] = mapped_column(Float)     # NDF（%DM）
    adf_pct: Mapped[Optional[float]] = mapped_column(Float)     # ADF（%DM）
    me_mj_kg: Mapped[Optional[float]] = mapped_column(Float)    # 代谢能 ME（MJ/kgDM）
    tdn_pct: Mapped[Optional[float]] = mapped_column(Float)     # 总消化养分 TDN（%DM）
    ca_pct: Mapped[Optional[float]] = mapped_column(Float)      # 钙 Ca（%DM）
    p_pct: Mapped[Optional[float]] = mapped_column(Float)       # 磷 P（%DM）
    dm_pct: Mapped[Optional[float]] = mapped_column(Float)      # 干物质 DM（%）

    # —— 经济 / 状态 ——
    price_yuan_kg: Mapped[Optional[float]] = mapped_column(Float)   # 单价（元/kg 鲜重）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # —— 扩展：Excel 全部原始指标（不丢数据）——
    extra_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class FeedPriceHistory(Base):
    __tablename__ = "feed_price_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[str] = mapped_column(String(36), ForeignKey("feeds.id"))
    price_yuan_kg: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
