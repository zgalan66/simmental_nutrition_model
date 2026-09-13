PRICE_SERVICE = '''from datetime import datetime, timedelta
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
'''

PRICE_API = '''from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.price_service import update_price, get_price_history

router = APIRouter()


class PriceUpdateReq(BaseModel):
    price_yuan_kg: float
    recorded_at: Optional[datetime] = None


@router.put("/{feed_id}", summary="更新原料价格（自动追加历史）")
async def set_price(feed_id: str, req: PriceUpdateReq, db: AsyncSession = Depends(get_db)):
    r = await update_price(db, feed_id, req.price_yuan_kg, req.recorded_at)
    if r is None:
        raise HTTPException(status_code=404, detail="原料不存在")
    return {"success": True, "data": r, "message": "价格已更新"}


@router.get("/{feed_id}/history", summary="价格历史")
async def history(feed_id: str, limit: int = 60, db: AsyncSession = Depends(get_db)):
    rows = await get_price_history(db, feed_id, limit)
    return {
        "success": True,
        "total": len(rows),
        "data": [
            {"price_yuan_kg": r.price_yuan_kg,
             "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None}
            for r in rows
        ],
    }
'''

SEED_SCRIPT = '''"""为所有原料造 7 天前 + 今天两条价格历史（用于测试预警）"""
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
'''

with open("services/price_service.py", "w", encoding="utf-8") as f:
    f.write(PRICE_SERVICE)
print("OK services/price_service.py")

with open("api/price.py", "w", encoding="utf-8") as f:
    f.write(PRICE_API)
print("OK api/price.py")

with open("seed_prices.py", "w", encoding="utf-8") as f:
    f.write(SEED_SCRIPT)
print("OK seed_prices.py")

# 挂载路由到 main.py
with open("main.py", "r", encoding="utf-8") as f:
    s = f.read()

if "api.price" not in s:
    old = 'app.include_router(feeds_router, prefix="/api/v1/feeds", tags=["原料"])'
    new = old + '\n\nfrom api.price import router as price_router\napp.include_router(price_router, prefix="/api/v1/price", tags=["价格"])'
    if old in s:
        s = s.replace(old, new)
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(s)
        print("OK main.py 已挂载价格路由")
    else:
        print("!! main.py 里没找到插入位置，请手动挂载")
else:
    print("SKIP main.py 已含价格路由")