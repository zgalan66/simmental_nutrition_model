"""
services/recommendation_engine.py — 配方优化引擎（模型B）【标准鲜重空间版】
=================================================================
变量 x_i = 第 i 种原料的 **鲜重用量(kg)**  ← 用户直觉空间，与你之前跑通的案例一致

求解：min 总成本 = Σ(price_i * x_i)
约束：
  - 配比上下限：lo_i <= x_i <= hi_i
  - 总重约束：Σ x_i = total_weight  (=100kg)
  - 营养（%DM 基准，严格线性化）：
        nutrient = Σ(val_i * dm_i * x_i) / Σ(dm_i * x_i)
        →  Σ(dm_i*(val_i - min_j))*x_i >= 0
        →  Σ(dm_i*(max_j - val_i))*x_i >= 0
        其中 val_i = 原料 %DM 营养值, dm_i = DM系数
  * 等价于"以 DM 为分母的加权"，与模型A(nutrition_engine) 口径一致

输出：最优配比 + 营养结果（模型A复核）+ 影子价格 + 约束状态
"""
import numpy as np
from typing import List, Dict, Any
from scipy.optimize import linprog

from .nutrition_engine import NUTRIENT_FIELDS, calculate_nutrition


def _get_val(feed, field: str) -> float:
    v = getattr(feed, field, None)
    if v is None:
        raise ValueError(f"原料「{feed.name}」缺少营养指标 {field}，无法参与优化")
    return float(v)


def optimize_formula(
    targets: Dict[str, Dict[str, float]],
    candidates: List[Dict[str, Any]],
    feeds_map: Dict[str, Any],
    total_weight: float = 100.0,
) -> Dict[str, Any]:
    """
    targets:   {field: {"min": x, "max": y, "slack": z}}  slack 可选，上限松弛
    candidates:[{name, feed_id, min_ratio, max_ratio}]
    feeds_map: {feed_id 或 name: Feed}
    """
    n = len(candidates)
    if n == 0:
        return {"status": "error", "message": "没有候选原料"}

    # —— 1. 组装原料 ——
    feed_objs, names, prices, dms, bounds = [], [], [], [], []
    for c in candidates:
        key = c.get("feed_id") or c["name"]
        feed = feeds_map.get(key)
        if feed is None:
            return {"status": "error", "message": f"候选原料「{c['name']}」未找到"}
        feed_objs.append(feed)
        names.append(feed.name)
        prices.append(float(feed.price_yuan_kg or 0.0))
        dm = _get_val(feed, "dm_pct") / 100.0
        if dm <= 0:
            return {"status": "error", "message": f"原料「{feed.name}」DM% 非法: {feed.dm_pct}"}
        dms.append(dm)

        lo = float(c.get("min_ratio", 0)) / 100.0 * total_weight
        hi = float(c.get("max_ratio", 100)) / 100.0 * total_weight
        bounds.append((lo, hi))

    dms = np.array(dms, dtype=float)
    prices = np.array(prices, dtype=float)

    # —— 2. 目标 & 总重约束（鲜重空间）——
    c = prices.copy()                               # min Σ price_i * x_i
    A_eq = np.ones((1, n), dtype=float)
    b_eq = np.array([total_weight], dtype=float)     # Σ x_i = total_weight

    # —— 3. 营养约束（严格线性化，与模型A口径一致）——
    #  nutrient = Σ(val_i*dm_i*x_i) / Σ(dm_i*x_i)
    #  下限: Σ(dm_i*(val_i - min_j)*x_i) >= 0  →  -Σ(dm_i*(val_i-min_j)*x_i) <= 0
    #  上限: Σ(dm_i*(max_j - val_i)*x_i) >= 0  →   Σ(dm_i*(max_j - val_i)*x_i) <= 0
    A_ub_rows, b_ub = [], []
    for field, lim in targets.items():
        if field not in NUTRIENT_FIELDS:
            continue
        vals = np.array([_get_val(f, field) for f in feed_objs], dtype=float)

        vmin = lim.get("min")
        vmax = lim.get("max")
        slack = float(lim.get("slack", 0.0))

        if vmin is not None:
            # -Σ(dm_i*(val_i - vmin))*x_i <= 0
            A_ub_rows.append(-dms * (vals - vmin))
            b_ub.append(0.0)
        if vmax is not None:
            # Σ(dm_i*(max_j + slack - val_i))*x_i <= 0
            A_ub_rows.append(dms * (vals - vmax - slack))
            b_ub.append(0.0)

    A_ub = np.vstack(A_ub_rows) if A_ub_rows else None
    b_ub = np.array(b_ub, dtype=float) if A_ub_rows else None

    # —— 4. 求解 ——
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")

    if not res.success:
        diag = _diagnose_infeasible(targets, candidates, feeds_map, total_weight, feed_objs, dms)
        return {"status": "infeasible", "message": "无可行解，请放宽约束或调整候选原料",
                "diagnosis": diag}

    x = np.maximum(res.x, 0.0)

    # —— 5. 组装结果（鲜重口径）——
    formula = []
    total_cost = 0.0
    items = []
    for i, ratio in enumerate(x):
        total_cost += ratio * prices[i]
        formula.append({
            "name": names[i],
            "ratio": round(float(ratio), 4),
            "ratio_pct": round(float(ratio) / total_weight * 100, 2),
            "price_yuan_kg": float(prices[i]),
            "dm_pct": round(dms[i] * 100, 2),
        })
        items.append({"feed": feed_objs[i], "ratio": float(ratio)})

    # —— 6. 模型A（DM加权）复核 ——
    nutrition = calculate_nutrition(items)

    # —— 7. 影子价格（scipy 版本兼容）——
    shadow_prices = []
    constraint_labels = []
    for field in targets:
        if field in NUTRIENT_FIELDS:
            constraint_labels.extend([f"{field}_min", f"{field}_max"])
    try:
        marginals = res.ineqlin.marginals
    except AttributeError:
        marginals = [None] * len(constraint_labels)
    for label, m in zip(constraint_labels, marginals):
        binding = bool(m is not None and abs(m) > 1e-8)
        shadow_prices.append({
            "constraint": label,
            "shadow_price": round(float(m), 6) if m is not None else None,
            "binding": binding,
        })

    # —— 8. 约束达标检查（基于模型A复核）——
    constraint_status = []
    all_ok = True
    for field, lim in targets.items():
        if field not in NUTRIENT_FIELDS:
            continue
        actual = nutrition.get(field)
        status = "ok"
        tol = float(lim.get("slack", 0.0)) + 1e-4
        if actual is None:
            status = "unknown"
        else:
            if lim.get("min") is not None and actual < lim["min"] - tol:
                status = "below_min"; all_ok = False
            elif lim.get("max") is not None and actual > lim["max"] + tol:
                status = "above_max"; all_ok = False
        constraint_status.append({
            "field": field, "actual": actual,
            "min": lim.get("min"), "max": lim.get("max"), "status": status,
        })

    return {
        "status": "optimal",
        "formula": formula,
        "total_cost": round(float(total_cost), 4),
        "cost_per_kg": round(float(total_cost) / total_weight, 4),
        "nutrition_result": nutrition,
        "constraint_status": constraint_status,
        "shadow_prices": shadow_prices,
        "missing_nutrients": [],
        "_all_constraints_ok": all_ok,
    }


def _diagnose_infeasible(targets, candidates, feeds_map, total_weight, feed_objs, dms) -> Dict[str, Any]:
    """对比候选原料的营养极值与约束要求，定位不可行原因"""
    diag = {"candidates": len(candidates), "notes": []}
    for field, lim in targets.items():
        if field not in NUTRIENT_FIELDS:
            continue
        # 折算到「纯原料鲜重」可得的营养极值（粗略：val*dm 加权后 / 平均dm）
        weighted = [_get_val(f, field) * dm for f, dm in zip(feed_objs, dms)]
        mn, mx = min(weighted), max(weighted)
        if lim.get("min") is not None and lim["min"] > mx + 1e-6:
            diag["notes"].append(f"{field} 要求 ≥{lim['min']}，但候选原料最高仅约 {mx:.1f}")
        if lim.get("max") is not None and lim["max"] < mn - 1e-6:
            diag["notes"].append(f"{field} 要求 ≤{lim['max']}，但候选原料最低已达约 {mn:.1f}")
    if not diag["notes"]:
        diag["notes"].append("可能是配比上下限(min_ratio/max_ratio)冲突，或总和约束与边界矛盾")
    return diag
