import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).order_by(Feed.p_pct.desc()))
        feeds = res.scalars().all()
        print("磷含量排序（从高到低）：\n")
        for f in feeds:
            if f.p_pct is not None:
                print(f"  {f.name:<25} p_pct={f.p_pct}")

asyncio.run(main())