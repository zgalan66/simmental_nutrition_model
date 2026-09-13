"""
services/feed_crud.py — 原料 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.feed_models import Feed


async def get_feed_by_name(db: AsyncSession, name: str) -> Optional[Feed]:
    result = await db.execute(select(Feed).where(Feed.name == name))
    return result.scalar_one_or_none()


async def get_feed_by_id(db: AsyncSession, feed_id: str) -> Optional[Feed]:
    return await db.get(Feed, feed_id)


async def list_feeds(db: AsyncSession, category: Optional[str] = None,
                     active_only: bool = True) -> List[Feed]:
    stmt = select(Feed)
    if category:
        stmt = stmt.where(Feed.category == category)
    if active_only:
        stmt = stmt.where(Feed.is_active == True)
    stmt = stmt.order_by(Feed.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_feed(db: AsyncSession, data: Dict[str, Any]) -> Feed:
    feed = Feed(**data)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return feed


async def update_feed(db: AsyncSession, feed: Feed, data: Dict[str, Any]) -> Feed:
    for k, v in data.items():
        setattr(feed, k, v)
    await db.commit()
    await db.refresh(feed)
    return feed


async def feeds_to_map(db: AsyncSession, feed_ids: List[str] = None) -> Dict[str, Feed]:
    """构造 {id: Feed, name: Feed} 双键映射"""
    stmt = select(Feed)
    if feed_ids:
        stmt = stmt.where(Feed.id.in_(feed_ids))
    result = await db.execute(stmt)
    m: Dict[str, Feed] = {}
    for f in result.scalars().all():
        m[f.id] = f
        m[f.name] = f
    return m
