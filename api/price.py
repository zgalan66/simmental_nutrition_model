from datetime import datetime
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
