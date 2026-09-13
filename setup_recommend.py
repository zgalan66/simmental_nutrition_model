RECOMMEND_ENGINE = '''"""配方推荐引擎（线性规划求最低成本）

思路：
- 变量 x_i = 第 i 种原料贡献的「干物质」占总 DM 的比例，sum(x_i) = 1
- 目标：最小化每 kg DM 成本 = sum(x_i * price_i / (dm_i/100))
- 约束：
  - 营养下限：sum(x_i * nutrient_i) >= min_j
  - 营养上限：sum(x_i * nutrient_i) <= max_j
  - 每种原料的 DM 比例范围
- 求解后用 nutrition_engine 精确重算营养和成本
"""
from typing import List, Dict, Any, Optional
import numpy as np
from scipy.optimize import linprog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.feed_models import Feed

NUTRIENT_FIELDS = ["cp_pct", "ndf_pct", "adf_pct", "me_mj_kg", "tdn_pct", "ca_pct", "p_pct"]


async def recommend_formula(
    db: AsyncSession,
    targets: Dict[str, Dict[str, Optional[float]]],
    candidates: List[Dict[str, Any]],
    total_weight: float = 100.0,
) -> Dict[str, Any]:
    if not candidates:
        return {"error": "候选原料不能为空"}

    names = [c["name"] for c in candidates]
    r = await db.execute(select(Feed).where(Feed.name.in_(names)))
    feed_map = {f.name: f for f in r.scalars().all()}
    missing = [n for n in names if n not in feed_map]
    if missing:
        return {"error": f"以下原料不存在: {missing}"}

    feeds = [feed_map[c["name"]] for c in candidates]
    n = len(feeds)

    dm_frac = np.array([(f.dm_pct or 100.0) / 100.0 for f in feeds])

    # 目标函数：每 kg DM 成本
    c_obj = np.array([
        ((f.price_yuan_kg or 0) / dm_frac[i]) for i, f in enumerate(feeds)
    ])

    A_ub, b_ub = [], []

    # 营养约束
    for field, bounds in (targets or {}).items():
        if field not in NUTRIENT_FIELDS:
            continue
        vals = np.array([
            (getattr(f, field, None) or 0.0) for f in feeds
        ])
        b = bounds or {}
        if b.get("min") is not None:
            A_ub.append(-vals)
            b_ub.append(-float(b["min"]))
        if b.get("max") is not None:
            A_ub.append(vals)
            b_ub.append(float(b["max"]))

    # 变量边界
    bounds_list = []
    for c in candidates:
        lo = max(0.0, float(c.get("min_ratio", 0)) / total_weight)
        hi = min(1.0, float(c.get("max_ratio", total_weight)) / total_weight)
        if lo > hi:
            lo, hi = hi, lo
        bounds_list.append((lo, hi))

    A_eq = [np.ones(n)]
    b_eq = [1.0]

    res = linprog(
        c=c_obj,
        A_ub=np.array(A_ub) if A_ub else None,
        b_ub=np.array(b_ub) if b_ub else None,
        A_eq=np.array(A_eq),
        b_eq=np.array(b_eq),
        bounds=bounds_list,
        method="highs",
    )

    if not res.success:
        return {
            "error": f"无法求解: {res.message}",
            "status": "infeasible",
        }

    x = res.x  # DM 贡献比
    wet = x / dm_frac
    wet_total = wet.sum()
    wet_pct = wet / wet_total if wet_total > 0 else wet

    formula = []
    for i, f in enumerate(feeds):
        ratio = wet_pct[i] * total_weight
        if ratio < 0.01:
            continue
        formula.append({
            "feed_id": f.id,
            "name": f.name,
            "ratio": round(ratio, 3),
            "ratio_pct": round(wet_pct[i] * 100, 2),
            "dm_contribution_pct": round(x[i] * 100, 2),
            "price_yuan_kg": f.price_yuan_kg,
        })

    from services.nutrition_engine import calculate_formula
    ing = [{"feed_id": it["feed_id"], "ratio": it["ratio"]} for it in formula]
    calc = await calculate_formula(db, ing)

    return {
        "status": "optimal",
        "formula": formula,
        "total_cost": calc.get("total_cost"),
        "cost_per_kg_dm": calc.get("total_cost_per_kg_dm"),
        "nutrition_result": calc.get("nutrition_result"),
        "total_dm_weight": calc.get("total_dm_weight"),
        "missing_nutrients": calc.get("missing_nutrients", []),
    }
'''

RECOMMEND_API = '''from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.recommendation_engine import recommend_formula

router = APIRouter()


class NutrientBound(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class CandidateItem(BaseModel):
    name: str
    min_ratio: float = 0.0
    max_ratio: float = 100.0


class RecommendReq(BaseModel):
    targets: Dict[str, NutrientBound] = {}
    candidates: List[CandidateItem]
    total_weight: float = 100.0


@router.post("/", summary="推荐配方（线性规划求最低成本）")
async def recommend(req: RecommendReq, db: AsyncSession = Depends(get_db)):
    targets = {k: v.model_dump() for k, v in req.targets.items()}
    candidates = [c.model_dump() for c in req.candidates]
    result = await recommend_formula(
        db, targets=targets, candidates=candidates, total_weight=req.total_weight
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "data": result}
'''

with open("services/recommendation_engine.py", "w", encoding="utf-8") as f:
    f.write(RECOMMEND_ENGINE)
print("OK services/recommendation_engine.py")

with open("api/recommend.py", "w", encoding="utf-8") as f:
    f.write(RECOMMEND_API)
print("OK api/recommend.py")