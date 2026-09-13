from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.formula_models import Formula
from services import template_service as svc
from services.recommendation_engine import optimize_formula

router = APIRouter()


class TemplateCreateReq(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    targets: Dict[str, Dict[str, Optional[float]]] = {}
    candidates: List[Dict[str, Any]] = []
    total_weight: float = 100.0
    is_default: bool = False


class TemplateUpdateReq(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    targets: Optional[Dict[str, Dict[str, Optional[float]]]] = None
    candidates: Optional[List[Dict[str, Any]]] = None
    total_weight: Optional[float] = None
    is_default: Optional[bool] = None


class ApplyReq(BaseModel):
    formula_name: Optional[str] = None
    user_id: Optional[str] = None


@router.get("/", summary="模板列表")
async def list_t(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    items = await svc.list_templates(db, category)
    return {"success": True, "data": [t.to_dict() for t in items], "total": len(items)}


@router.get("/{tid}", summary="模板详情")
async def get_t(tid: str, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, tid)
    if not t:
        raise HTTPException(404, "模板不存在")
    return {"success": True, "data": t.to_dict()}


@router.post("/", summary="创建模板")
async def create_t(req: TemplateCreateReq, db: AsyncSession = Depends(get_db)):
    try:
        t = await svc.create_template(db, req.model_dump())
        return {"success": True, "data": t.to_dict(), "message": "已创建"}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.put("/{tid}", summary="更新模板")
async def update_t(tid: str, req: TemplateUpdateReq, db: AsyncSession = Depends(get_db)):
    t = await svc.update_template(db, tid, req.model_dump(exclude_unset=True))
    if not t:
        raise HTTPException(404, "模板不存在")
    return {"success": True, "data": t.to_dict(), "message": "已更新"}


@router.delete("/{tid}", summary="删除模板")
async def delete_t(tid: str, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_template(db, tid)
    if not ok:
        raise HTTPException(404, "模板不存在")
    return {"success": True, "message": "已删除"}


@router.post("/{tid}/apply", summary="按模板跑优化（不保存）")
async def apply_t(tid: str, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, tid)
    if not t:
        raise HTTPException(404, "模板不存在")
    result = await optimize_formula(
        db, targets=t.targets or {}, candidates=t.candidates or [],
        total_weight=t.total_weight or 100.0,
    )
    if "error" in result:
        raise HTTPException(400, result)
    return {"success": True, "template_name": t.name, "data": result}


@router.post("/{tid}/apply-save", summary="按模板优化并保存为配方")
async def apply_save(tid: str, req: ApplyReq, db: AsyncSession = Depends(get_db)):
    t = await svc.get_template(db, tid)
    if not t:
        raise HTTPException(404, "模板不存在")
    result = await optimize_formula(
        db, targets=t.targets or {}, candidates=t.candidates or [],
        total_weight=t.total_weight or 100.0,
    )
    if "error" in result:
        raise HTTPException(400, result)

    name = req.formula_name or f"{t.name}-{datetime.utcnow().strftime('%m%d%H%M')}"
    ing = [{"feed_id": it["feed_id"], "name": it["name"], "ratio": it["ratio"]} for it in result["formula"]]

    formula = Formula(
        name=name, user_id=req.user_id, ingredients=ing,
        nutrition_result=result["nutrition_result"], total_cost=result["total_cost"],
    )
    db.add(formula)
    await db.commit()
    await db.refresh(formula)

    return {
        "success": True,
        "message": f"已保存配方「{name}」",
        "formula_id": formula.id,
        "template_name": t.name,
        "formula_data": {
            "id": formula.id,
            "name": formula.name,
            "ingredients": formula.ingredients,
            "nutrition_result": formula.nutrition_result,
            "total_cost": formula.total_cost,
            "cost_per_kg_dm": result.get("cost_per_kg_dm"),
            "constraint_status": result.get("constraint_status"),
            "shadow_prices": result.get("shadow_prices"),
        },
    }
