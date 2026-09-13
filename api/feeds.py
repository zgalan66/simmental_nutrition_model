from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.feed_models import Feed

router = APIRouter()

class FeedCreateReq(BaseModel):
    name: str
    category: Optional[str] = None
    cp_pct: Optional[float] = None
    ndf_pct: Optional[float] = None
    me_mj_kg: Optional[float] = None
    price_yuan_kg: Optional[float] = None

class FeedUpdateReq(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cp_pct: Optional[float] = None
    ndf_pct: Optional[float] = None
    me_mj_kg: Optional[float] = None
    price_yuan_kg: Optional[float] = None
    is_active: Optional[bool] = None

@router.post("/", summary="创建原料")
async def create_feed(req: FeedCreateReq, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Feed).where(Feed.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"原料 {req.name} 已存在")
    feed = Feed(**req.model_dump())
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return {"success": True, "data": feed.to_dict(), "message": "原料创建成功"}

@router.get("/", summary="原料列表")
async def list_feeds(
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Feed)
    if category:
        stmt = stmt.where(Feed.category == category)
    if active_only:
        stmt = stmt.where(Feed.is_active == True)
    stmt = stmt.order_by(Feed.name)
    result = await db.execute(stmt)
    feeds = result.scalars().all()
    return {"success": True, "data": [f.to_dict() for f in feeds], "total": len(feeds)}

@router.get("/{feed_id}", summary="获取单个原料")
async def get_feed(feed_id: str, db: AsyncSession = Depends(get_db)):
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="原料不存在")
    return {"success": True, "data": feed.to_dict()}

@router.put("/{feed_id}", summary="更新原料")
async def update_feed(feed_id: str, req: FeedUpdateReq, db: AsyncSession = Depends(get_db)):
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="原料不存在")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    await db.commit()
    await db.refresh(feed)
    return {"success": True, "data": feed.to_dict(), "message": "原料更新成功"}

@router.delete("/{feed_id}", summary="删除原料")
async def delete_feed(feed_id: str, db: AsyncSession = Depends(get_db)):
    feed = await db.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="原料不存在")
    feed.is_active = False
    await db.commit()
    return {"success": True, "message": "原料已停用"}
