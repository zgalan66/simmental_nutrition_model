OPTIMIZE_ENGINE = '''"""配方优化引擎（改进版）

改进点：
1. 约束直接在"鲜重"空间做（不再有 DM 转换误差）
2. 返回影子价格（每种营养的边际成本）
3. 无解时给出可行性诊断
4. 返回每条约束的达成情况
"""
from typing import List, Dict, Any, Optional
import numpy as np
from scipy.optimize import linprog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.feed_models import Feed

NUTRIENT_FIELDS = ["cp_pct", "ndf_pct", "adf_pct", "me_mj_kg", "tdn_pct", "ca_pct", "p_pct"]


def _diagnose_infeasible(targets, candidates, feeds):
    hints = []
    for field, bounds in (targets or {}).items():
        if field not in NUTRIENT_FIELDS:
            continue
        vals = [getattr(f, field, None) for f in feeds]
        vals = [v for v in vals if v is not None]
        if not vals:
            hints.append(f"{field}: 所有候选原料都缺该指标")
            continue
        vmin, vmax = min(vals), max(vals)
        b = bounds or {}
        if b.get("min") is not None and b["min"] > vmax:
            hints.append(f"{field} 下限 {b['min']} 超过原料最高值 {round(vmax,2)}，无法达到")
        if b.get("max") is not None and b["max"] < vmin:
            hints.append(f"{field} 上限 {b['max']} 低于原料最低值 {round(vmin,2)}，无法达到")
    total_min = sum(float(c.get("min_ratio", 0)) for c in candidates)
    total_max = sum(float(c.get("max_ratio", 100)) for c in candidates)
    if total_min > 100:
        hints.append(f"原料最小比例之和 {total_min}% > 100%")
    if total_max < 100:
        hints.append(f"原料最大比例之和 {total_max}% < 100%")
    if not hints:
        hints.append("可能是多个约束互相冲突，尝试放宽营养范围或增加候选原料")
    return hints


async def optimize_formula(
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
    dm = np.array([(f.dm_pct or 100.0) / 100.0 for f in feeds])
    price = np.array([f.price_yuan_kg if f.price_yuan_kg is not None else 0.0 for f in feeds])

    A_ub, b_ub = [], []
    constraint_labels = []

    for field, bounds in (targets or {}).items():
        if field not in NUTRIENT_FIELDS:
            continue
        nvals = np.array([(getattr(f, field, None) or 0.0) for f in feeds])
        b = bounds or {}
        if b.get("min") is not None:
            min_j = float(b["min"])
            A_ub.append(-dm * (nvals - min_j))
            b_ub.append(0.0)
            constraint_labels.append(f"{field}_min")
        if b.get("max") is not None:
            max_j = float(b["max"])
            A_ub.append(dm * (nvals - max_j))
            b_ub.append(0.0)
            constraint_labels.append(f"{field}_max")

    bounds_list = []
    for c in candidates:
        lo = max(0.0, float(c.get("min_ratio", 0)))
        hi = min(total_weight, float(c.get("max_ratio", total_weight)))
        if lo > hi:
            lo, hi = hi, lo
        bounds_list.append((lo, hi))

    A_eq = [np.ones(n)]
    b_eq = [total_weight]

    res = linprog(
        c=price,
        A_ub=np.array(A_ub) if A_ub else None,
        b_ub=np.array(b_ub) if b_ub else None,
        A_eq=np.array(A_eq),
        b_eq=np.array(b_eq),
        bounds=bounds_list,
        method="highs",
    )

    if not res.success:
        return {
            "status": "infeasible",
            "error": f"无法求解: {res.message}",
            "diagnosis": _diagnose_infeasible(targets, candidates, feeds),
        }

    x = res.x
    formula = []
    for i, f in enumerate(feeds):
        if x[i] < 1e-4:
            continue
        formula.append({
            "feed_id": f.id,
            "name": f.name,
            "ratio": round(float(x[i]), 4),
            "ratio_pct": round(float(x[i] / total_weight * 100), 2),
            "price_yuan_kg": f.price_yuan_kg,
            "dm_pct": f.dm_pct,
        })

    from services.nutrition_engine import calculate_formula
    ing = [{"feed_id": it["feed_id"], "ratio": it["ratio"]} for it in formula]
    calc = await calculate_formula(db, ing)

    shadow_prices = []
    try:
        marginals = res.ineqlin.marginals
        for idx, label in enumerate(constraint_labels):
            if idx >= len(marginals):
                break
            sp = float(marginals[idx])
            shadow_prices.append({
                "constraint": label,
                "shadow_price": round(sp, 4),
                "binding": abs(sp) > 1e-6,
            })
    except Exception:
        pass

    nutrition = calc.get("nutrition_result", {})
    constraint_status = []
    for field, bounds in (targets or {}).items():
        if field not in NUTRIENT_FIELDS:
            continue
        actual = nutrition.get(field)
        if actual is None:
            continue
        b = bounds or {}
        status = "ok"
        if b.get("min") is not None and actual < b["min"] - 1e-6:
            status = "below_min"
        elif b.get("max") is not None and actual > b["max"] + 1e-6:
            status = "above_max"
        constraint_status.append({
            "field": field,
            "actual": actual,
            "min": b.get("min"),
            "max": b.get("max"),
            "status": status,
        })

    return {
        "status": "optimal",
        "formula": formula,
        "total_cost": calc.get("total_cost"),
        "cost_per_kg_dm": calc.get("total_cost_per_kg_dm"),
        "nutrition_result": nutrition,
        "constraint_status": constraint_status,
        "shadow_prices": shadow_prices,
        "missing_nutrients": calc.get("missing_nutrients", []),
    }
'''

OPTIMIZE_API = '''from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.recommendation_engine import optimize_formula

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
'''

with open("services/recommendation_engine.py", "w", encoding="utf-8") as f:
    f.write(OPTIMIZE_ENGINE)
print("OK services/recommendation_engine.py")

with open("api/recommend.py", "w", encoding="utf-8") as f:
    f.write(OPTIMIZE_API)
print("OK api/recommend.py")