import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).order_by(Feed.category, Feed.name))
        feeds = res.scalars().all()
        for f in feeds:
            print(f"{f.name}")

asyncio.run(main())