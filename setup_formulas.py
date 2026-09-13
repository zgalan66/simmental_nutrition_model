NUTRITION_ENGINE = '''"""配方营养计算引擎

输入: [{"feed_id": "...", "ratio": 60.0}, ...]
     也支持 {"name": "玉米", "ratio": 60.0}（按名字查）
ratio 是相对重量（kg、%，都行），内部会归一化。

营养指标（CP / NDF / ADF / ME / TDN / Ca / P）都以 DM 为基准加权，
最终返回混合配方的营养浓度（% DM 或 MJ/kgDM）。
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.feed_models import Feed

NUTRIENT_FIELDS = ["cp_pct", "ndf_pct", "adf_pct", "me_mj_kg", "tdn_pct", "ca_pct", "p_pct"]


async def calculate_formula(db: AsyncSession, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not ingredients:
        return {"error": "配料不能为空"}

    total_ratio = sum(float(x["ratio"]) for x in ingredients)
    if total_ratio <= 0:
        return {"error": "配料比例总和必须大于 0"}

    ids = [x["feed_id"] for x in ingredients if x.get("feed_id")]
    names = [x["name"] for x in ingredients if x.get("name")]

    by_id, by_name = {}, {}
    if ids:
        r = await db.execute(select(Feed).where(Feed.id.in_(ids)))
        for f in r.scalars().all():
            by_id[f.id] = f
    if names:
        r = await db.execute(select(Feed).where(Feed.name.in_(names)))
        for f in r.scalars().all():
            by_name[f.name] = f

    missing = []
    resolved = []
    for item in ingredients:
        feed = None
        if item.get("feed_id"):
            feed = by_id.get(item["feed_id"])
        if feed is None and item.get("name"):
            feed = by_name.get(item["name"])
        if feed is None:
            missing.append(item.get("feed_id") or item.get("name") or "?")
            continue
        resolved.append((item, feed))

    if missing:
        return {"error": f"以下原料不存在: {missing}"}

    details = []
    total_dm_kg = 0.0
    total_cost = 0.0
    contrib = {f: 0.0 for f in NUTRIENT_FIELDS}
    missing_nutrients = set()

    for item, feed in resolved:
        ratio = float(item["ratio"])
        dm = feed.dm_pct if feed.dm_pct is not None else 100.0
        dm_kg = ratio * dm / 100.0
        total_dm_kg += dm_kg

        if feed.price_yuan_kg is not None:
            total_cost += ratio * feed.price_yuan_kg

        row = {
            "feed_id": feed.id,
            "name": feed.name,
            "ratio": ratio,
            "ratio_pct": round(ratio / total_ratio * 100, 2),
            "dm_pct": feed.dm_pct,
            "price_yuan_kg": feed.price_yuan_kg,
        }

        for field in NUTRIENT_FIELDS:
            v = getattr(feed, field, None)
            if v is None:
                missing_nutrients.add(field)
                continue
            contrib[field] += dm_kg * v
            row[field] = v

        details.append(row)

    nutrition = {}
    if total_dm_kg > 0:
        for field in NUTRIENT_FIELDS:
            nutrition[field] = round(contrib[field] / total_dm_kg, 3)

    nutrition["dm_pct"] = round(total_dm_kg / total_ratio * 100, 2) if total_ratio > 0 else 0

    return {
        "nutrition_result": nutrition,
        "total_cost": round(total_cost, 4),
        "total_cost_per_kg_dm": round(total_cost / total_dm_kg, 4) if total_dm_kg > 0 else None,
        "total_weight": round(total_ratio, 3),
        "total_dm_weight": round(total_dm_kg, 3),
        "ingredient_details": details,
        "missing_nutrients": sorted(missing_nutrients),
    }
'''

FORMULAS_API = '''from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db
from models.formula_models import Formula
from services.nutrition_engine import calculate_formula

router = APIRouter()


class IngredientItem(BaseModel):
    feed_id: Optional[str] = None
    name: Optional[str] = None
    ratio: float = Field(gt=0, description="相对重量或百分比")


class FormulaCreateReq(BaseModel):
    name: Optional[str] = None
    user_id: Optional[str] = None
    ingredients: List[IngredientItem]


class FormulaUpdateReq(BaseModel):
    name: Optional[str] = None
    ingredients: Optional[List[IngredientItem]] = None


def _formula_dict(f: Formula) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "user_id": f.user_id,
        "ingredients": f.ingredients,
        "nutrition_result": f.nutrition_result,
        "total_cost": f.total_cost,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }


@router.post("/calculate", summary="配方营养计算（不保存）")
async def calculate_only(req: FormulaCreateReq, db: AsyncSession = Depends(get_db)):
    ing = [x.model_dump(exclude_none=True) for x in req.ingredients]
    result = await calculate_formula(db, ing)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "data": result}


@router.post("/", summary="创建配方")
async def create_formula(req: FormulaCreateReq, db: AsyncSession = Depends(get_db)):
    ing = [x.model_dump(exclude_none=True) for x in req.ingredients]
    calc = await calculate_formula(db, ing)
    if "error" in calc:
        raise HTTPException(status_code=400, detail=calc["error"])

    formula = Formula(
        name=req.name or "未命名配方",
        user_id=req.user_id,
        ingredients=ing,
        nutrition_result=calc["nutrition_result"],
        total_cost=calc["total_cost"],
    )
    db.add(formula)
    await db.commit()
    await db.refresh(formula)
    return {"success": True, "data": _formula_dict(formula), "calc": calc, "message": "配方已创建"}


@router.get("/", summary="配方列表")
async def list_formulas(user_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Formula)
    if user_id:
        stmt = stmt.where(Formula.user_id == user_id)
    stmt = stmt.order_by(desc(Formula.updated_at))
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {"success": True, "data": [_formula_dict(f) for f in items], "total": len(items)}


@router.get("/{formula_id}", summary="获取配方")
async def get_formula(formula_id: str, db: AsyncSession = Depends(get_db)):
    f = await db.get(Formula, formula_id)
    if not f:
        raise HTTPException(status_code=404, detail="配方不存在")
    recalc = await calculate_formula(db, f.ingredients or [])
    return {"success": True, "data": _formula_dict(f), "recalc": recalc}


@router.put("/{formula_id}", summary="更新配方")
async def update_formula(formula_id: str, req: FormulaUpdateReq, db: AsyncSession = Depends(get_db)):
    f = await db.get(Formula, formula_id)
    if not f:
        raise HTTPException(status_code=404, detail="配方不存在")

    if req.name is not None:
        f.name = req.name
    if req.ingredients is not None:
        ing = [x.model_dump(exclude_none=True) for x in req.ingredients]
        calc = await calculate_formula(db, ing)
        if "error" in calc:
            raise HTTPException(status_code=400, detail=calc["error"])
        f.ingredients = ing
        f.nutrition_result = calc["nutrition_result"]
        f.total_cost = calc["total_cost"]

    await db.commit()
    await db.refresh(f)
    return {"success": True, "data": _formula_dict(f), "message": "配方已更新"}


@router.delete("/{formula_id}", summary="删除配方")
async def delete_formula(formula_id: str, db: AsyncSession = Depends(get_db)):
    f = await db.get(Formula, formula_id)
    if not f:
        raise HTTPException(status_code=404, detail="配方不存在")
    await db.delete(f)
    await db.commit()
    return {"success": True, "message": "配方已删除"}
'''

with open("services/nutrition_engine.py", "w", encoding="utf-8") as f:
    f.write(NUTRITION_ENGINE)
print("OK services/nutrition_engine.py")

with open("api/formulas.py", "w", encoding="utf-8") as f:
    f.write(FORMULAS_API)
print("OK api/formulas.py")