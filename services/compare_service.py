"""配方对比：营养、成本、原料差异"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.formula_models import Formula

NUTRIENT_FIELDS = ["cp_pct", "ndf_pct", "adf_pct", "me_mj_kg", "tdn_pct", "ca_pct", "p_pct", "dm_pct"]

FIELD_LABELS = {
    "cp_pct": "粗蛋白 CP (%)",
    "ndf_pct": "中性洗涤纤维 NDF (%)",
    "adf_pct": "酸性洗涤纤维 ADF (%)",
    "me_mj_kg": "代谢能 ME (MJ/kg)",
    "tdn_pct": "总可消化养分 TDN (%)",
    "ca_pct": "钙 Ca (%)",
    "p_pct": "磷 P (%)",
    "dm_pct": "干物质 DM (%)",
}


async def compare_formulas(db: AsyncSession, id_a: str, id_b: str) -> Dict[str, Any]:
    fa = await db.get(Formula, id_a)
    fb = await db.get(Formula, id_b)
    if not fa:
        return {"error": f"配方 A 不存在: {id_a}"}
    if not fb:
        return {"error": f"配方 B 不存在: {id_b}"}

    na = fa.nutrition_result or {}
    nb = fb.nutrition_result or {}

    nutrition_diff = []
    for field in NUTRIENT_FIELDS:
        va = na.get(field)
        vb = nb.get(field)
        if va is None and vb is None:
            continue
        diff = None
        if va is not None and vb is not None:
            diff = round(vb - va, 3)
        nutrition_diff.append({
            "field": field,
            "label": FIELD_LABELS.get(field, field),
            "A": va,
            "B": vb,
            "diff_B_minus_A": diff,
        })

    cost_a = fa.total_cost or 0
    cost_b = fb.total_cost or 0
    cost_diff = round(cost_b - cost_a, 3)
    cost_diff_pct = round((cost_b - cost_a) / cost_a * 100, 2) if cost_a > 0 else None

    ing_a = {it.get("name") or it.get("feed_id"): it.get("ratio", 0) for it in (fa.ingredients or [])}
    ing_b = {it.get("name") or it.get("feed_id"): it.get("ratio", 0) for it in (fb.ingredients or [])}

    all_names = sorted(set(ing_a.keys()) | set(ing_b.keys()))
    ingredient_diff = []
    for name in all_names:
        ra = ing_a.get(name, 0)
        rb = ing_b.get(name, 0)
        ingredient_diff.append({
            "name": name,
            "A_ratio": round(ra, 3),
            "B_ratio": round(rb, 3),
            "diff_B_minus_A": round(rb - ra, 3),
        })

    only_in_a = [n for n in ing_a if n not in ing_b]
    only_in_b = [n for n in ing_b if n not in ing_a]

    cheaper = None
    if cost_a < cost_b:
        cheaper = "A"
    elif cost_b < cost_a:
        cheaper = "B"

    return {
        "formula_A": {
            "id": fa.id, "name": fa.name,
            "total_cost": cost_a, "ingredients": fa.ingredients,
        },
        "formula_B": {
            "id": fb.id, "name": fb.name,
            "total_cost": cost_b, "ingredients": fb.ingredients,
        },
        "cost": {
            "A": cost_a, "B": cost_b,
            "diff_B_minus_A": cost_diff,
            "diff_pct": cost_diff_pct,
            "cheaper": cheaper,
        },
        "nutrition_diff": nutrition_diff,
        "ingredient_diff": ingredient_diff,
        "only_in_A": only_in_a,
        "only_in_B": only_in_b,
    }
