import asyncio, sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from database import AsyncSessionLocal, engine
from models.feed_models import Feed
from models.base import Base
from sqlalchemy import select

EXCEL = r"D:\HuaweiMoveData\Users\wangj\Desktop\公牛\原料含量.xlsx"


def num(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    if not s:
        return None
    if "~" in s or "-" in s:
        parts = re.split(r"[-~]", s)
        nums = []
        for p in parts:
            p = p.strip()
            try:
                nums.append(float(p))
            except ValueError:
                pass
        if len(nums) >= 2:
            return round((nums[0] + nums[1]) / 2, 4)
        if len(nums) == 1:
            return nums[0]
        return None
    try:
        return float(s)
    except ValueError:
        return None


def find_col(cols, *keywords):
    for c in cols:
        cs = str(c).strip()
        for kw in keywords:
            if kw in cs:
                return cs
    return None


def auto_header(raw):
    for i, row in raw.iterrows():
        vals = "".join(str(x) for x in row.values if pd.notna(x))
        if "原料名称" in vals:
            return i
    return 0


def is_degradation_row(name, cp):
    if cp is None:
        return True
    try:
        return float(cp) < 1
    except (TypeError, ValueError):
        return False


def guess_category(name):
    for kw, cat in [
        ("豆粕", "蛋白质"), ("大豆", "蛋白质"), ("菜籽", "蛋白质"),
        ("棉籽", "蛋白质"), ("花生", "蛋白质"), ("DDGS", "蛋白质"),
        ("玉米", "能量"), ("麦麸", "能量"), ("大麦", "能量"),
        ("淀粉", "能量"), ("豆油", "能量"),
        ("青贮", "粗饲料"), ("秸秆", "粗饲料"), ("苜蓿", "粗饲料"),
        ("石粉", "矿物质"), ("磷酸", "矿物质"), ("氧化镁", "矿物质"),
        ("盐", "矿物质"), ("小苏打", "矿物质"),
        ("尿素", "添加剂"), ("预混", "添加剂"), ("维生素", "添加剂"),
        ("赖氨酸", "添加剂"), ("蛋氨酸", "添加剂"),
    ]:
        if kw in name:
            return cat
    return "其他"


async def import_feeds():
    print("=" * 60)
    print("导入原料（v2）")
    print("=" * 60)

    if not os.path.exists(EXCEL):
        print("ERROR: 找不到", EXCEL)
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    raw = pd.read_excel(EXCEL, header=None, sheet_name=0)
    hdr = auto_header(raw)
    print(f"表头行: 第 {hdr + 1} 行")

    df = pd.read_excel(EXCEL, header=hdr, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)
    print(f"总行数: {len(df)}")
    print(f"列: {cols[:10]}")

    name_col = find_col(cols, "原料名称") or cols[0]
    cp_col = find_col(cols, "粗蛋白", "CP")
    me_col = find_col(cols, "代谢能", "ME")
    dm_col = find_col(cols, "干物质", "DM")
    ndf_col = find_col(cols, "NDF")
    adf_col = find_col(cols, "ADF")
    ca_col = find_col(cols, "钙", "Ca")
    p_col = find_col(cols, "磷", "P")
    price_col = find_col(cols, "单价", "价格")
    cat_col = find_col(cols, "类别")

    print(f"\n字段映射:")
    print(f"  name={name_col}  cp={cp_col}  me={me_col}  ca={ca_col}  price={price_col}")

    async with AsyncSessionLocal() as db:
        ins = upd = skip = 0
        for _, row in df.iterrows():
            raw_name = row[name_col]
            if pd.isna(raw_name) or str(raw_name).strip() == "":
                continue
            name = str(raw_name).strip()

            cp_val = num(row[cp_col]) if cp_col else None
            if is_degradation_row(name, cp_val):
                skip += 1
                continue

            res = await db.execute(select(Feed).where(Feed.name == name))
            feed = res.scalar_one_or_none()
            is_new = feed is None
            if is_new:
                feed = Feed(name=name)
                db.add(feed)

            if cat_col and not pd.isna(row[cat_col]):
                feed.category = str(row[cat_col]).strip()
            elif not feed.category:
                feed.category = guess_category(name)

            if dm_col:
                v = num(row[dm_col])
                if v is not None: feed.dm_pct = v
            if cp_col and cp_val is not None:
                feed.cp_pct = cp_val
            if ndf_col:
                v = num(row[ndf_col])
                if v is not None: feed.ndf_pct = v
            if adf_col:
                v = num(row[adf_col])
                if v is not None: feed.adf_pct = v
            if me_col:
                v = num(row[me_col])
                if v is not None: feed.me_mj_kg = v
            if ca_col:
                v = num(row[ca_col])
                if v is not None: feed.ca_pct = v
            if p_col:
                v = num(row[p_col])
                if v is not None: feed.p_pct = v
            if price_col:
                v = num(row[price_col])
                if v is not None: feed.price_yuan_kg = v

            if is_new: ins += 1
            else: upd += 1

        await db.commit()
        print(f"\n完成! 新增 {ins}, 更新 {upd}, 跳过降解行 {skip}")

if __name__ == "__main__":
    asyncio.run(import_feeds())