RECOMMEND_API = '''from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.recommendation_engine import optimize_formula
from models.formula_models import Formula

router = APIRouter()


class NutrientBound(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class CandidateItem(BaseModel):
    name: str
    min_ratio: float = 0.0
    max_ratio: float = 100.0


class OptimizeReq(BaseModel):
    targets: Dict[str, NutrientBound] = {}
    candidates: List[CandidateItem]
    total_weight: float = 100.0


class SaveOptimizeReq(BaseModel):
    name: str
    user_id: Optional[str] = None
    targets: Dict[str, NutrientBound] = {}
    candidates: List[CandidateItem]
    total_weight: float = 100.0


@router.post("/", summary="配方优化（最低成本，含影子价格）")
async def optimize(req: OptimizeReq, db: AsyncSession = Depends(get_db)):
    targets = {k: v.model_dump() for k, v in req.targets.items()}
    candidates = [c.model_dump() for c in req.candidates]
    result = await optimize_formula(
        db, targets=targets, candidates=candidates, total_weight=req.total_weight
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "data": result}


@router.post("/save", summary="优化并保存为配方")
async def optimize_and_save(req: SaveOptimizeReq, db: AsyncSession = Depends(get_db)):
    targets = {k: v.model_dump() for k, v in req.targets.items()}
    candidates = [c.model_dump() for c in req.candidates]

    result = await optimize_formula(
        db, targets=targets, candidates=candidates, total_weight=req.total_weight
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)

    ing = [
        {"feed_id": it["feed_id"], "name": it["name"], "ratio": it["ratio"]}
        for it in result["formula"]
    ]

    formula = Formula(
        name=req.name,
        user_id=req.user_id,
        ingredients=ing,
        nutrition_result=result["nutrition_result"],
        total_cost=result["total_cost"],
    )
    db.add(formula)
    await db.commit()
    await db.refresh(formula)

    return {
        "success": True,
        "message": f"已保存配方「{req.name}」",
        "formula_id": formula.id,
        "formula_data": {
            "id": formula.id,
            "name": formula.name,
            "ingredients": formula.ingredients,
            "nutrition_result": formula.nutrition_result,
            "total_cost": formula.total_cost,
            "cost_per_kg_dm": result.get("cost_per_kg_dm"),
            "shadow_prices": result.get("shadow_prices"),
            "constraint_status": result.get("constraint_status"),
        },
    }
'''

with open("api/recommend.py", "w", encoding="utf-8") as f:
    f.write(RECOMMEND_API)
print("OK api/recommend.py 已更新（含 /save 接口）")