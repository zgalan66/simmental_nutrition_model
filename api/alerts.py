\
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.alert_service import (
    check_price_alerts, check_nutrition_alerts, get_alerts,
    acknowledge_alert, resolve_alert, create_alert_rule, get_alert_rules, init_default_alert_rules
)
router = APIRouter()

class RuleCreateReq(BaseModel):
    name: str
    alert_type: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    conditions: dict = {}
    severity: str = "warning"

class CheckReq(BaseModel):
    feed_id: Optional[str] = None
    formula_id: Optional[str] = None
    user_id: Optional[str] = None

@router.post("/init-defaults")
async def init_defaults(db: AsyncSession = Depends(get_db)):
    created = await init_default_alert_rules(db)
    return {"success": True, "message": f"初始化了 {created} 条规则"}

@router.post("/rules")
async def create_rule(req: RuleCreateReq, db: AsyncSession = Depends(get_db)):
    ok, msg, rule = await create_alert_rule(db, req.name, req.alert_type, req.conditions, req.target_type, req.target_id, req.severity)
    return {"success": ok, "data": rule.to_dict() if rule else None, "message": msg}

@router.get("/rules")
async def list_rules(alert_type: Optional[str] = None, enabled_only: bool = False, db: AsyncSession = Depends(get_db)):
    rules = await get_alert_rules(db, alert_type, enabled_only)
    return {"success": True, "data": [r.to_dict() for r in rules]}

@router.post("/check/price")
async def check_price(req: CheckReq, db: AsyncSession = Depends(get_db)):
    triggered = await check_price_alerts(db, feed_id=req.feed_id, user_id=req.user_id)
    return {"success": True, "data": {"count": len(triggered), "alerts": triggered}}

@router.post("/check/nutrition")
async def check_nutrition(req: CheckReq, db: AsyncSession = Depends(get_db)):
    triggered = await check_nutrition_alerts(db, formula_id=req.formula_id, user_id=req.user_id)
    return {"success": True, "data": {"count": len(triggered), "alerts": triggered}}

@router.get("")
async def list_alerts(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)):
    records, total = await get_alerts(db, page=page, page_size=page_size)
    return {"success": True, "data": {"items": [r.to_dict() for r in records], "total": total}}

@router.get("/active")
async def active_alerts(db: AsyncSession = Depends(get_db)):
    records, total = await get_alerts(db, resolved=False, acknowledged=False, page_size=50)
    return {"success": True, "data": {"items": [r.to_dict() for r in records], "total": total}}

@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from models.alert_models import AlertRecord
    total = (await db.execute(select(func.count(AlertRecord.id)))).scalar()
    active = (await db.execute(select(func.count(AlertRecord.id)).where(AlertRecord.is_resolved == False))).scalar()
    return {"success": True, "data": {"total": total, "active": active}}

@router.put("/{alert_id}/acknowledge")
async def ack(alert_id: str, user_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    ok, msg = await acknowledge_alert(db, alert_id, user_id)
    return {"success": ok, "message": msg}

@router.put("/{alert_id}/resolve")
async def resolve(alert_id: str, db: AsyncSession = Depends(get_db)):
    ok, msg = await resolve_alert(db, alert_id)
    return {"success": ok, "message": msg}
