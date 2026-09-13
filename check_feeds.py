import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).order_by(Feed.category, Feed.name))
        feeds = res.scalars().all()
        print(f"共 {len(feeds)} 条原料\n")
        print(f"{'名称':<18} {'类别':<6} {'CP%':>6} {'ME':>6} {'Ca%':>6} {'价格':>6}")
        print("-" * 58)
        for f in feeds[:15]:
            cp = f"{f.cp_pct:6.1f}" if f.cp_pct else "    -"
            me = f"{f.me_mj_kg:6.2f}" if f.me_mj_kg else "    -"
            ca = f"{f.ca_pct:6.2f}" if f.ca_pct else "    -"
            pr = f"{f.price_yuan_kg:6.2f}" if f.price_yuan_kg else "    -"
            print(f"{f.name:<18} {str(f.category):<6}{cp}{me}{ca}{pr}")
        print("...")

        no_cp = [f.name for f in feeds if f.cp_pct is None]
        no_me = [f.name for f in feeds if f.me_mj_kg is None]
        no_price = [f.name for f in feeds if f.price_yuan_kg is None]
        print()
        if no_cp: print(f"WARNING: 缺CP: {no_cp[:8]}")
        if no_me: print(f"WARNING: 缺ME: {no_me[:8]}")
        if no_price: print(f"WARNING: 缺价格: {no_price[:8]}")
        if not no_cp and not no_me and not no_price:
            print("ALL KEY FIELDS COMPLETE")

        from collections import Counter
        c = Counter(f.category for f in feeds)
        print("\n各分类数量:")
        for k, v in c.most_common():
            print(f"  {k}: {v}")

asyncio.run(check())