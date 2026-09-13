from typing import List, Optional
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
