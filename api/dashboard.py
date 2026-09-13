\
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.dashboard_service import (
    get_dashboard_overview, get_feed_price_trend, get_formula_cost_trend,
    get_nutrition_analysis, get_feed_usage_analysis, get_stage_comparison, export_dashboard_report
)
router = APIRouter()

@router.get("/overview")
async def overview(range_type: str = "30d", db: AsyncSession = Depends(get_db)):
    data = await get_dashboard_overview(db, range_type=range_type)
    return {"success": True, "data": data}

@router.get("/price-trend")
async def price_trend(range_type: str = "30d", db: AsyncSession = Depends(get_db)):
    data = await get_feed_price_trend(db, range_type=range_type)
    return {"success": True, "data": data}

@router.get("/formula-cost-trend")
async def cost_trend(range_type: str = "30d", db: AsyncSession = Depends(get_db)):
    data = await get_formula_cost_trend(db, range_type=range_type)
    return {"success": True, "data": data}

@router.get("/nutrition-analysis")
async def nutrition_analysis(db: AsyncSession = Depends(get_db)):
    data = await get_nutrition_analysis(db)
    return {"success": True, "data": data}

@router.get("/usage-analysis")
async def usage_analysis(db: AsyncSession = Depends(get_db)):
    data = await get_feed_usage_analysis(db)
    return {"success": True, "data": data}

@router.get("/stage-comparison")
async def stage_comparison(db: AsyncSession = Depends(get_db)):
    data = await get_stage_comparison(db)
    return {"success": True, "data": data}

@router.post("/export")
async def export(db: AsyncSession = Depends(get_db)):
    import base64
    excel_bytes = await export_dashboard_report(db)
    return {"success": True, "data": {"filename": "dashboard.xlsx", "content_base64": base64.b64encode(excel_bytes).decode()}}
