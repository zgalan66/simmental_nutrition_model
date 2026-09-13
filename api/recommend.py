"""
api/recommend.py — 配方推荐接口（调用模型B优化引擎）
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.feed_crud import feeds_to_map
from services.recommendation_engine import optimize_formula

router = APIRouter()


class CandidateReq(BaseModel):
    name: Optional[str] = None
    feed_id: Optional[str] = None
    min_ratio: float = 0
    max_ratio: float = 100


class RecommendReq(BaseModel):
    targets: Dict[str, Dict[str, float]] = Field(
        ..., example={"cp_pct": {"min": 14, "max": 18}, "me_mj_kg": {"min": 9, "max": 12}}
    )
    candidates: List[CandidateReq]
    total_weight: float = 100.0


@router.post("/")
async def recommend(req: RecommendReq, db: AsyncSession = Depends(get_db)):
    feed_ids = [c.feed_id for c in req.candidates if c.feed_id]
    feeds_map = await feeds_to_map(db, feed_ids)

    # 补充：若只给了 name，也按 name 查一次
    for c in req.candidates:
        if not c.feed_id and c.name:
            from services.feed_crud import get_feed_by_name
            f = await get_feed_by_name(db, c.name)
            if f:
                feeds_map[c.name] = f

    if not feeds_map:
        raise HTTPException(status_code=400, detail="没有可用的原料数据，请先导入原料")

    result = optimize_formula(
        targets=req.targets,
        candidates=[c.model_dump() for c in req.candidates],
        feeds_map=feeds_map,
        total_weight=req.total_weight,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    if result.get("status") == "infeasible":
        return {
            "success": False,
            "data": result,
            "message": "无可行解，请放宽约束或调整候选原料（详见 diagnosis）",
        }

    return {"success": True, "data": result, "message": "配方优化完成"}
