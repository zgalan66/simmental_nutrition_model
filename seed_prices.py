"""为所有原料造 7 天前 + 今天两条价格历史（用于测试预警）"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from database import AsyncSessionLocal
from models.feed_models import Feed, FeedPriceHistory

OLD_PRICE_FACTOR = 0.85


async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Feed).where(Feed.is_active.is_(True)))
        feeds = list(r.scalars().all())

        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        count = 0

        for f in feeds:
            if f.price_yuan_kg is None:
                continue
            await db.execute(delete(FeedPriceHistory).where(FeedPriceHistory.feed_id == f.id))
            old_price = round(f.price_yuan_kg * OLD_PRICE_FACTOR, 4)
            db.add(FeedPriceHistory(feed_id=f.id, price_yuan_kg=old_price, recorded_at=seven_days_ago))
            db.add(FeedPriceHistory(feed_id=f.id, price_yuan_kg=f.price_yuan_kg, recorded_at=now))
            count += 1

        await db.commit()
        print(f"OK 为 {count} 种原料写入了价格历史")
        pct = round((1 / OLD_PRICE_FACTOR - 1) * 100, 1)
        print(f"   规则：7 天前 = 当前价格 x {OLD_PRICE_FACTOR}（即上涨约 {pct}%）")


if __name__ == "__main__":
    asyncio.run(main())
