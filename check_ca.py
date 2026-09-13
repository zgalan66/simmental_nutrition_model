import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).order_by(Feed.ca_pct.desc()))
        feeds = res.scalars().all()
        print("钙含量排序（从高到低，前 20 条）：\n")
        for f in feeds[:20]:
            if f.ca_pct is not None:
                print(f"  {f.name:<28} ca_pct={f.ca_pct}")

        print("\n--- 重点检查（应为 0 的原料）---\n")
        res2 = await db.execute(select(Feed).where(Feed.name.in_([
            "尿素（缓释）", "硫酸铵", "豆粕（43%）", "过瘤胃赖氨酸（包被）",
            "饲料级豆油", "玉米", "磷酸氢钙", "石粉（碳酸钙）"
        ])))
        for f in res2.scalars().all():
            print(f"  {f.name:<28} ca_pct={f.ca_pct}")

asyncio.run(main())