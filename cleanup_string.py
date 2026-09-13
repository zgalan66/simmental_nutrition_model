import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select, delete

async def cleanup():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).where(Feed.name == "string"))
        bad = res.scalar_one_or_none()
        if bad:
            await db.delete(bad)
            await db.commit()
            print("已删除 'string' 脏数据")
        else:
            print("没找到 'string'")

        # 顺便看看还有没有空的
        res2 = await db.execute(select(Feed).where(Feed.cp_pct.is_(None), Feed.me_mj_kg.is_(None), Feed.ca_pct.is_(None)))
        empties = res2.scalars().all()
        if empties:
            print(f"\n还有 {len(empties)} 条三字段全空的:")
            for f in empties:
                print(f"  id={f.id} name='{f.name}' category='{f.category}'")

asyncio.run(cleanup())