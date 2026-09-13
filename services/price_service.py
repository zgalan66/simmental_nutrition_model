from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.feed_models import Feed, FeedPriceHistory


async def update_price(db: AsyncSession, feed_id: str, new_price: float,
                       recorded_at: Optional[datetime] = None) -> Optional[Dict]:
    feed = await db.get(Feed, feed_id)
    if not feed:
        return None
    old = feed.price_yuan_kg
    feed.price_yuan_kg = new_price
    h = FeedPriceHistory(
        feed_id=feed_id,
        price_yuan_kg=new_price,
        recorded_at=recorded_at or datetime.utcnow(),
    )
    db.add(h)
    await db.commit()
    change_pct = None
    if old is not None and old > 0:
        change_pct = round((new_price - old) / old * 100, 2)
    return {
        "feed_id": feed_id,
        "feed_name": feed.name,
        "old_price": old,
        "new_price": new_price,
        "change_pct": change_pct,
    }


async def get_price_history(db: AsyncSession, feed_id: str, limit: int = 60):
    stmt = select(FeedPriceHistory).where(
        FeedPriceHistory.feed_id == feed_id
    ).order_by(desc(FeedPriceHistory.recorded_at)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
