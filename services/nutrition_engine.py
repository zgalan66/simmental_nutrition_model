"""
services/nutrition_engine.py — 营养计算引擎（模型A：L1→L3）
输入：原料列表 + 各原料鲜重用量(kg)
输出：DM加权后的综合营养指标（%DM 基准）
"""
from typing import List, Dict, Any


# 参与加权计算的 7 项核心指标（与 optimize_engine 完全一致）
NUTRIENT_FIELDS = ["cp_pct", "ndf_pct", "adf_pct", "me_mj_kg", "tdn_pct", "ca_pct", "p_pct"]


def _require(feed, field: str):
    """缺失关键营养指标 → 直接报错（不再静默用 0）"""
    val = getattr(feed, field, None)
    if val is None:
        raise ValueError(f"原料「{feed.name}」缺少营养指标 {field}，无法参与营养计算")
    return float(val)


def calculate_nutrition(feeds_with_ratio) -> Dict[str, Any]:
    """
    feeds_with_ratio: list of dict，每项含：
        - feed: Feed 对象（含 cp_pct, dm_pct, ...）
        - ratio: 鲜重用量(kg)
    返回：DM 加权后的营养结果 dict
    """
    total_fresh_kg = 0.0
    total_dm_kg = 0.0
    weighted = {f: 0.0 for f in NUTRIENT_FIELDS}
    ca_pct_val = 0.0
    p_pct_val = 0.0

    for item in feeds_with_ratio:
        feed = item["feed"]
        ratio = float(item.get("ratio", 0.0))
        if ratio <= 0:
            continue
        dm_pct = _require(feed, "dm_pct")       # DM%
        dm_kg = ratio * dm_pct / 100.0           # 该原料贡献的干物质(kg)

        total_fresh_kg += ratio
        total_dm_kg += dm_kg

        for f in NUTRIENT_FIELDS:
            v = _require(feed, f)
            weighted[f] += v * dm_kg              # 按干物质加权

    if total_dm_kg <= 0:
        raise ValueError("配方总干物质为 0，请检查各原料 DM% 与用量")

    # 加权后除以总 DM → 得到 %DM 基准的营养浓度
    result = {
        "total_fresh_kg": round(total_fresh_kg, 4),
        "total_dm_kg": round(total_dm_kg, 4),
        "dm_pct": round(total_dm_kg / total_fresh_kg * 100, 2) if total_fresh_kg > 0 else 0,
    }
    for f in NUTRIENT_FIELDS:
        result[f] = round(weighted[f] / total_dm_kg, 4)

    return result


def calculate_formula(formula, feeds_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    兼容 Formula 对象的便捷入口：
    formula.ingredients = {feed_id: ratio_kg}
    feeds_map = {feed_id: Feed}
    """
    items = []
    for fid, ratio in (formula.ingredients or {}).items():
        feed = feeds_map.get(fid)
        if feed is None:
            raise ValueError(f"配方引用的原料 {fid} 不存在")
        items.append({"feed": feed, "ratio": float(ratio)})
    return calculate_nutrition(items)
