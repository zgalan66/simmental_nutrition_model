import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from database import AsyncSessionLocal, engine
from models.feed_models import Feed
from models.base import Base
from sqlalchemy import select

EXCEL = r"D:\HuaweiMoveData\Users\wangj\Desktop\公牛\原料含量.xlsx"


def find_col(cols, *keywords):
    for c in cols:
        cs = str(c).strip()
        for kw in keywords:
            if kw in cs:
                return cs
    return None


def num(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    if "~" in s:
        p = s.split("~")
        try:
            return round((float(p[0]) + float(p[1])) / 2, 4)
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None


async def import_feeds():
    print("=" * 50)
    print("Import feeds from:", EXCEL)
    if not os.path.exists(EXCEL):
        print("ERROR: file not found")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    df = pd.read_excel(EXCEL, header=1)
    cols = list(df.columns)
    print("Rows:", len(df))
    print("Columns:", cols)

    name_col = find_col(cols, "原料", "名称") or cols[0]
    cat_col = find_col(cols, "类别", "分类")
    dm_col = find_col(cols, "干物质", "DM")
    cp_col = find_col(cols, "粗蛋白", "CP")
    ndf_col = find_col(cols, "NDF")
    adf_col = find_col(cols, "ADF")
    tdn_col = find_col(cols, "TDN")
    me_col = find_col(cols, "代谢能", "ME")
    ca_col = find_col(cols, "钙", "Ca")
    p_col = find_col(cols, "磷", "P")
    price_col = find_col(cols, "价格", "单价")

    print("Detected columns:")
    print("  name:", name_col)
    print("  cp:", cp_col, "| me:", me_col, "| ca:", ca_col, "| price:", price_col)

    async with AsyncSessionLocal() as db:
        ins = 0
        upd = 0
        for idx, row in df.iterrows():
            raw = row[name_col]
            if pd.isna(raw) or str(raw).strip() == "":
                continue
            name = str(raw).strip()

            res = await db.execute(select(Feed).where(Feed.name == name))
            feed = res.scalar_one_or_none()
            is_new = feed is None
            if is_new:
                feed = Feed(name=name)
                db.add(feed)

            if cat_col:
                v = row[cat_col]
                if not pd.isna(v):
                    feed.category = str(v).strip()
            if dm_col:
                v = num(row[dm_col])
                if v is not None:
                    feed.dm_pct = v
            if cp_col:
                v = num(row[cp_col])
                if v is not None:
                    feed.cp_pct = v
            if ndf_col:
                v = num(row[ndf_col])
                if v is not None:
                    feed.ndf_pct = v
            if adf_col:
                v = num(row[adf_col])
                if v is not None:
                    feed.adf_pct = v
            if tdn_col:
                v = num(row[tdn_col])
                if v is not None:
                    feed.tdn_pct = v
            if me_col:
                v = num(row[me_col])
                if v is not None:
                    feed.me_mj_kg = v
            if ca_col:
                v = num(row[ca_col])
                if v is not None:
                    feed.ca_pct = v
            if p_col:
                v = num(row[p_col])
                if v is not None:
                    feed.p_pct = v
            if price_col:
                v = num(row[price_col])
                if v is not None:
                    feed.price_yuan_kg = v

            if not feed.category:
                for kw, cat in [("玉米", "能量"), ("麦麸", "能量"), ("豆粕", "蛋白"),
                                 ("苜蓿", "粗饲料"), ("青贮", "粗饲料"), ("石粉", "矿物质"), ("盐", "矿物质")]:
                    if kw in name:
                        feed.category = cat
                        break

            if is_new:
                ins += 1
            else:
                upd += 1

        await db.commit()
        print(f"\nDone. Inserted {ins}, Updated {upd}")


if __name__ == "__main__":
    asyncio.run(import_feeds())