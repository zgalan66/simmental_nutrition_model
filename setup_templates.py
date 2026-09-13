TEMPLATE_MODEL = '''import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class ConstraintTemplate(Base):
    __tablename__ = "constraint_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    targets: Mapped[dict] = mapped_column(JSON, default=dict)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    total_weight: Mapped[float] = mapped_column(Float, default=100.0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
'''

TEMPLATE_SERVICE = '''from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.template_models import ConstraintTemplate


async def list_templates(db: AsyncSession, category: Optional[str] = None):
    stmt = select(ConstraintTemplate)
    if category:
        stmt = stmt.where(ConstraintTemplate.category == category)
    stmt = stmt.order_by(desc(ConstraintTemplate.is_default), ConstraintTemplate.name)
    r = await db.execute(stmt)
    return list(r.scalars().all())


async def get_template(db: AsyncSession, tid: str):
    return await db.get(ConstraintTemplate, tid)


async def create_template(db: AsyncSession, data: Dict[str, Any]):
    t = ConstraintTemplate(**data)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def update_template(db: AsyncSession, tid: str, data: Dict[str, Any]):
    t = await db.get(ConstraintTemplate, tid)
    if not t:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return t


async def delete_template(db: AsyncSession, tid: str) -> bool:
    t = await db.get(ConstraintTemplate, tid)
    if not t:
        return False
    await db.delete(t)
    await db.commit()
    return True
'''

TEMPLATE_API = '''from datetime import datetime
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
'''

SEED_TEMPLATES = '''"""初始化西门塔尔公牛各阶段的标准约束模板"""
import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal, engine
from models.base import Base
from models.template_models import ConstraintTemplate


TEMPLATES = [
    {
        "name": "架子牛期",
        "category": "架子牛",
        "description": "300-400kg 生长期，日增重 0.8-1.0kg，注重骨架发育",
        "targets": {
            "cp_pct": {"min": 12.0, "max": 14.5},
            "me_mj_kg": {"min": 9.5, "max": 11.0},
            "ndf_pct": {"min": 35.0, "max": 50.0},
            "ca_pct": {"min": 0.4, "max": 0.7},
            "p_pct": {"min": 0.25, "max": 0.4},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 40},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 25},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 12},
            {"name": "苜蓿（初花期）", "min_ratio": 10, "max_ratio": 40},
            {"name": "玉米秸秆青贮（无籽粒）", "min_ratio": 0, "max_ratio": 40},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "育肥前期",
        "category": "育肥期",
        "description": "400-500kg，日增重 1.0-1.2kg，快速增重阶段",
        "targets": {
            "cp_pct": {"min": 12.0, "max": 14.5},
            "me_mj_kg": {"min": 10.0, "max": 11.5},
            "ndf_pct": {"min": 25.0, "max": 40.0},
            "ca_pct": {"min": 0.5, "max": 0.8},
            "p_pct": {"min": 0.3, "max": 0.5},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 55},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 20},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 15},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 30},
            {"name": "全株玉米青贮（30% DM）", "min_ratio": 0, "max_ratio": 35},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "育肥后期",
        "category": "育肥期",
        "description": "500kg 以上，日增重 1.2-1.4kg，冲刺出栏",
        "targets": {
            "cp_pct": {"min": 11.0, "max": 13.0},
            "me_mj_kg": {"min": 11.0, "max": 12.0},
            "ndf_pct": {"min": 20.0, "max": 35.0},
            "ca_pct": {"min": 0.5, "max": 0.8},
            "p_pct": {"min": 0.3, "max": 0.5},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 20, "max_ratio": 65},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 15},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 12},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 20},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "妊娠期母牛",
        "category": "母牛",
        "description": "妊娠中期至后期，控制膘情，保证胎儿发育",
        "targets": {
            "cp_pct": {"min": 11.0, "max": 13.0},
            "me_mj_kg": {"min": 9.0, "max": 11.0},
            "ndf_pct": {"min": 35.0, "max": 55.0},
            "ca_pct": {"min": 0.4, "max": 0.8},
            "p_pct": {"min": 0.25, "max": 0.4},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 30},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 20},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 10},
            {"name": "苜蓿（初花期）", "min_ratio": 15, "max_ratio": 50},
            {"name": "玉米秸秆青贮（无籽粒）", "min_ratio": 0, "max_ratio": 50},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "泌乳期母牛",
        "category": "母牛",
        "description": "哺乳期，日产奶 8-12kg，高能量高蛋白",
        "targets": {
            "cp_pct": {"min": 13.0, "max": 16.0},
            "me_mj_kg": {"min": 10.0, "max": 12.0},
            "ndf_pct": {"min": 28.0, "max": 45.0},
            "ca_pct": {"min": 0.6, "max": 1.0},
            "p_pct": {"min": 0.35, "max": 0.55},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 50},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 25},
            {"name": "豆粕（43%）", "min_ratio": 5, "max_ratio": 20},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 35},
            {"name": "全株玉米青贮（30% DM）", "min_ratio": 0, "max_ratio": 35},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1.5},
        ],
        "is_default": True,
    },
]


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    created = 0
    async with AsyncSessionLocal() as db:
        for td in TEMPLATES:
            existing = await db.execute(select(ConstraintTemplate).where(ConstraintTemplate.name == td["name"]))
            if existing.scalar_one_or_none():
                print(f"  跳过（已存在）: {td['name']}")
                continue
            db.add(ConstraintTemplate(**td))
            print(f"  新增: {td['name']}")
            created += 1
        await db.commit()

    print(f"OK 共创建 {created} 个模板")


if __name__ == "__main__":
    asyncio.run(main())
'''

with open("models/template_models.py", "w", encoding="utf-8") as f:
    f.write(TEMPLATE_MODEL)
print("OK models/template_models.py")

with open("services/template_service.py", "w", encoding="utf-8") as f:
    f.write(TEMPLATE_SERVICE)
print("OK services/template_service.py")

with open("api/templates.py", "w", encoding="utf-8") as f:
    f.write(TEMPLATE_API)
print("OK api/templates.py")

with open("seed_templates.py", "w", encoding="utf-8") as f:
    f.write(SEED_TEMPLATES)
print("OK seed_templates.py")

# 挂载路由到 main.py
with open("main.py", "r", encoding="utf-8") as f:
    s = f.read()

if "api.templates" not in s:
    old = 'app.include_router(recommend_router, prefix="/api/v1/recommend", tags=["推荐"])'
    new = old + '\n\nfrom api.templates import router as templates_router\napp.include_router(templates_router, prefix="/api/v1/templates", tags=["约束模板"])'
    if old in s:
        s = s.replace(old, new)
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(s)
        print("OK main.py 已挂载模板路由")
    else:
        print("!! main.py 里没找到插入位置，请手动挂载")
else:
    print("SKIP main.py 已含模板路由")