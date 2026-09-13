FEED_MODELS = '''import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class Feed(Base):
    __tablename__ = "feeds"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    dm_pct: Mapped[Optional[float]] = mapped_column(Float)
    cp_pct: Mapped[Optional[float]] = mapped_column(Float)
    ndf_pct: Mapped[Optional[float]] = mapped_column(Float)
    adf_pct: Mapped[Optional[float]] = mapped_column(Float)
    me_mj_kg: Mapped[Optional[float]] = mapped_column(Float)
    tdn_pct: Mapped[Optional[float]] = mapped_column(Float)
    ca_pct: Mapped[Optional[float]] = mapped_column(Float)
    p_pct: Mapped[Optional[float]] = mapped_column(Float)
    price_yuan_kg: Mapped[Optional[float]] = mapped_column(Float)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class FeedPriceHistory(Base):
    __tablename__ = "feed_price_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feed_id: Mapped[str] = mapped_column(String(36), ForeignKey("feeds.id"))
    price_yuan_kg: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
'''

IMPORT_SCRIPT = '''"""从 data/原料含量.xlsx 批量导入原料到数据库"""
import asyncio
import os
import re
import sys

import pandas as pd
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(__file__))
from database import AsyncSessionLocal, engine
from models.feed_models import Feed
from models.base import Base

EXCEL_FILE = "data/原料含量.xlsx"

COLUMN_MAP = {
    "干物质含量（DM%）": "dm_pct",
    "代谢能（MJ/kgDM）": "me_mj_kg",
    "粗蛋白 CP（% DM）": "cp_pct",
    "钙（% DM）": "ca_pct",
    "磷（% DM）": "p_pct",
    "NDFDM（%DM）": "ndf_pct",
    "ADFDM（%DM）": "adf_pct",
    "TDN 含量（% DM）": "tdn_pct",
}

CATEGORY_RULES = [
    (["青贮", "秸秆", "草", "秧", "苜蓿", "构树", "高丹"], "粗饲料"),
    (["豆粕", "豆饼", "花生饼", "棉籽", "菜籽", "玉米蛋白", "DDGS", "胚芽"], "蛋白饲料"),
    (["豆油", "脂肪", "脂肪酸"], "油脂"),
    (["预混料", "维生素", "微量元素", "赖氨酸", "蛋氨酸", "烟酸", "B族"], "添加剂"),
    (["石粉", "磷酸", "氧化镁", "氯化钾", "盐", "小苏打", "硫酸", "尿素"], "矿物质"),
    (["玉米", "大麦", "小麦", "淀粉", "麦麸", "玉米皮", "喷浆"], "能量饲料"),
]


def infer_category(name):
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return cat
    return "其他"


def parse_range(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if s in ("", "-", "—", "–", "nan", "NaN"):
        return None
    s = s.replace("～", "~").replace("－", "-").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        pass
    m = re.match(r"^([\\d.]+)[~\\-]([\\d.]+)$", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return round((a + b) / 2, 4)
    m = re.match(r"^[><]=?([\\d.]+)$", s)
    if m:
        return float(m.group(1))
    return None


async def ensure_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    if not os.path.exists(EXCEL_FILE):
        print(f"找不到文件: {EXCEL_FILE}")
        print(f"请把 原料含量.xlsx 复制到 {os.path.abspath('data')}")
        return

    print(f"读取 Excel: {EXCEL_FILE}")
    df_raw = pd.read_excel(EXCEL_FILE, sheet_name=0, header=None)

    header_row = None
    for i in range(min(5, len(df_raw))):
        if any("原料名称" in str(c) for c in df_raw.iloc[i]):
            header_row = i
            break
    if header_row is None:
        print("找不到表头行（应该含 原料名称）")
        return
    print(f"表头在第 {header_row + 1} 行")

    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df_raw.iloc[header_row]]
    df = df.iloc[header_row + 1:].reset_index(drop=True)

    name_col = None
    for c in df.columns:
        if "原料名称" in c:
            name_col = c
            break
    if name_col is None:
        print("找不到原料名称列")
        return

    df = df.dropna(subset=[name_col])
    print(f"共 {len(df)} 行数据")

    created = updated = skipped = 0

    async with AsyncSessionLocal() as db:
        for _, row in df.iterrows():
            name = row[name_col]
            if not name or pd.isna(name):
                skipped += 1
                continue
            name = str(name).strip()
            if not name:
                skipped += 1
                continue

            data = {}
            extra = {}
            for c in df.columns:
                c_str = str(c).strip()
                val = row[c]
                if c_str == name_col:
                    continue
                if c_str in COLUMN_MAP:
                    parsed = parse_range(val)
                    if parsed is not None:
                        data[COLUMN_MAP[c_str]] = parsed
                else:
                    parsed = parse_range(val)
                    if parsed is not None:
                        extra[c_str] = parsed
                    else:
                        if val is None:
                            continue
                        try:
                            if pd.isna(val):
                                continue
                        except (TypeError, ValueError):
                            pass
                        s = str(val).strip()
                        if s and s not in ("-", "—", "nan"):
                            extra[c_str] = s

            data["extra_data"] = extra
            data["category"] = infer_category(name)

            existing = await db.execute(select(Feed).where(Feed.name == name))
            feed = existing.scalar_one_or_none()
            if feed:
                for k, v in data.items():
                    setattr(feed, k, v)
                updated += 1
                print(f"  更新: {name}")
            else:
                feed = Feed(name=name, **data)
                db.add(feed)
                created += 1
                print(f"  新增: {name}")

        await db.commit()

    print("=" * 50)
    print(f"完成！新增 {created} 条，更新 {updated} 条，跳过 {skipped} 条")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(ensure_tables())
    asyncio.run(main())
'''

with open("models/feed_models.py", "w", encoding="utf-8") as f:
    f.write(FEED_MODELS)
print("OK models/feed_models.py 已重写")

with open("import_feeds.py", "w", encoding="utf-8") as f:
    f.write(IMPORT_SCRIPT)
print("OK import_feeds.py 已创建")