
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import numpy as np
from models.alert_models import AlertRule, AlertRecord

logger = logging.getLogger(__name__)

DEFAULT_RULES = [
    {"name": "原料价格上涨预警", "alert_type": "price", "target_type": "global",
     "conditions": {"threshold_pct": 10, "direction": "up", "lookback_days": 7}, "severity": "warning"},
    {"name": "原料价格暴跌预警", "alert_type": "price", "target_type": "global",
     "conditions": {"threshold_pct": 15, "direction": "down", "lookback_days": 7}, "severity": "info"},
    {"name": "原料价格超限预警", "alert_type": "price", "target_type": "global",
     "conditions": {"abs_price_max": 5.0}, "severity": "critical"},
    {"name": "粗蛋白偏离预警", "alert_type": "nutrition", "target_type": "global",
     "conditions": {"indicators": ["cp_pct"], "cp_pct_min": 16.0, "cp_pct_max": 19.0}, "severity": "warning"},
    {"name": "NDF异常预警", "alert_type": "nutrition", "target_type": "global",
     "conditions": {"indicators": ["ndf_pct"], "ndf_pct_min": 25.0, "ndf_pct_max": 45.0}, "severity": "warning"},
    {"name": "代谢能不足预警", "alert_type": "nutrition", "target_type": "global",
     "conditions": {"indicators": ["me_mj_kg"], "me_mj_kg_min": 10.5, "me_mj_kg_max": 12.0}, "severity": "critical"},
]

async def init_default_alert_rules(db: AsyncSession) -> int:
    created = 0
    for rd in DEFAULT_RULES:
        existing = await db.execute(select(AlertRule).where(AlertRule.name == rd["name"]))
        if existing.scalar_one_or_none():
            continue
        rule = AlertRule(**rd)
        db.add(rule)
        created += 1
    await db.commit()
    return created

async def check_price_alerts(db: AsyncSession, feed_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
    triggered = []
    rules_stmt = select(AlertRule).where(AlertRule.alert_type == "price", AlertRule.enabled == True)
    rules = (await db.execute(rules_stmt)).scalars().all()
    if not rules:
        return triggered

    from models.feed_models import Feed, FeedPriceHistory
    if feed_id:
        feed = await db.get(Feed, feed_id)
        feeds = [feed] if feed else []
    else:
        feeds = (await db.execute(select(Feed).where(Feed.is_active == True))).scalars().all()

    for feed in feeds:
        if not feed:
            continue
        price_stmt = select(FeedPriceHistory).where(
            FeedPriceHistory.feed_id == feed.id
        ).order_by(desc(FeedPriceHistory.recorded_at)).limit(60)
        prices = list((await db.execute(price_stmt)).scalars().all())
        if len(prices) < 2:
            continue

        current_price = prices[0].price_yuan_kg
        latest_date = prices[0].recorded_at

        for rule in rules:
            conditions = rule.conditions or {}
            threshold_pct = float(conditions.get("threshold_pct", 10))
            lookback_days = int(conditions.get("lookback_days", 7))
            direction = conditions.get("direction", "both")
            cutoff = latest_date - timedelta(days=lookback_days)
            historical = [p for p in prices if p.recorded_at <= cutoff]

            if historical:
                old_price = historical[0].price_yuan_kg
                if old_price > 0:
                    change_pct = (current_price - old_price) / old_price * 100
                    if direction in ("up", "both") and change_pct >= threshold_pct:
                        rec = await _make_price_alert(db, rule, feed, current_price, old_price, change_pct, f"价格上涨 {change_pct:.1f}%", rule.severity or "warning")
                        if rec:
                            triggered.append(rec)
                    elif direction in ("down", "both") and change_pct <= -threshold_pct:
                        rec = await _make_price_alert(db, rule, feed, current_price, old_price, change_pct, f"价格下跌 {abs(change_pct):.1f}%", rule.severity or "warning")
                        if rec:
                            triggered.append(rec)

            abs_max = conditions.get("abs_price_max")
            if abs_max is not None and current_price >= float(abs_max):
                rec = await _make_price_alert(db, rule, feed, current_price, None, None, f"价格超上限 ¥{abs_max}", rule.severity or "warning")
                if rec:
                    triggered.append(rec)
    return triggered

async def _make_price_alert(db, rule, feed, current_price, old_price, change_pct, reason, severity) -> Optional[Dict]:
    existing = await db.execute(
        select(AlertRecord).where(
            AlertRecord.alert_type == "price", AlertRecord.target_id == feed.id,
            AlertRecord.is_resolved == False, AlertRecord.title.like(f"%{reason[:15]}%")
        )
    )
    if existing.scalar_one_or_none():
        return None

    title = f"⚠️ {feed.name} {reason}"
    msg = f"原料「{feed.name}」当前价格 ¥{current_price}/kg"
    if old_price and change_pct is not None:
        msg += f"，较之前 ¥{old_price}/kg 变化 {change_pct:+.1f}%"
    msg += f"。{reason}。"

    record = AlertRecord(
        rule_id=rule.id, alert_type="price", target_type="feed", target_id=feed.id,
        target_name=feed.name, title=title, message=msg, severity=severity,
        snapshot={"current_price": current_price, "old_price": old_price, "change_pct": change_pct}
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record.to_dict()

async def check_nutrition_alerts(db: AsyncSession, formula_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
    from models.formula_models import Formula
    triggered = []
    rules_stmt = select(AlertRule).where(AlertRule.alert_type == "nutrition", AlertRule.enabled == True)
    if formula_id:
        rules_stmt = rules_stmt.where((AlertRule.target_id == formula_id) | (AlertRule.target_id.is_(None)))
    rules = (await db.execute(rules_stmt)).scalars().all()
    if not rules:
        return triggered

    standards = {
        "cp_pct": {"min": 16.0, "max": 19.0, "name": "粗蛋白"},
        "ndf_pct": {"min": 25.0, "max": 45.0, "name": "NDF"},
        "me_mj_kg": {"min": 10.5, "max": 12.0, "name": "代谢能"},
    }

    fstmt = select(Formula)
    if formula_id:
        fstmt = fstmt.where(Formula.id == formula_id)
    formulas = (await db.execute(fstmt)).scalars().all()

    for formula in formulas:
        if not hasattr(formula, 'nutrition_result') or not formula.nutrition_result:
            continue
        nr = formula.nutrition_result
        for rule in rules:
            conditions = rule.conditions or {}
            indicators = conditions.get("indicators", list(standards.keys()))
            for ind in indicators:
                if ind not in standards:
                    continue
                val = nr.get(ind)
                if val is None:
                    continue
                std = standards[ind]
                min_v = float(conditions.get(f"{ind}_min", std["min"]))
                max_v = conditions.get(f"{ind}_max", std["max"])
                if max_v is not None:
                    max_v = float(max_v)

                issue = None
                if val < min_v:
                    issue = f"低于标准 {min_v}"
                elif max_v is not None and val > max_v:
                    issue = f"超过标准 {max_v}"

                if issue:
                    existing = await db.execute(
                        select(AlertRecord).where(
                            AlertRecord.alert_type == "nutrition", AlertRecord.target_id == formula.id,
                            AlertRecord.is_resolved == False, AlertRecord.message.like(f"%{ind}%")
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    title = f"⚠️ 配方「{formula.name or '未命名'}」营养偏离"
                    msg = f"配方「{formula.name or '未命名'}」的{std['name']}为 {val}，{issue}（标准 {min_v}-{max_v or '∞'}）。"
                    record = AlertRecord(
                        rule_id=rule.id, alert_type="nutrition", target_type="formula",
                        target_id=formula.id, target_name=formula.name or "未命名",
                        title=title, message=msg, severity=rule.severity or "warning",
                        snapshot={"indicator": ind, "value": val, "min": min_v, "max": max_v}
                    )
                    db.add(record)
                    triggered.append(record.to_dict())
    if triggered:
        await db.commit()
    return triggered

async def get_alerts(db: AsyncSession, alert_type=None, severity=None, resolved=None, acknowledged=None, page=1, page_size=20):
    stmt = select(AlertRecord)
    count_stmt = select(func.count(AlertRecord.id))
    for val, col in [(alert_type, AlertRecord.alert_type), (severity, AlertRecord.severity)]:
        if val:
            stmt = stmt.where(col == val)
            count_stmt = count_stmt.where(col == val)
    if resolved is not None:
        stmt = stmt.where(AlertRecord.is_resolved == resolved)
        count_stmt = count_stmt.where(AlertRecord.is_resolved == resolved)
    if acknowledged is not None:
        stmt = stmt.where(AlertRecord.is_acknowledged == acknowledged)
    total = (await db.execute(count_stmt)).scalar()
    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(AlertRecord.triggered_at)).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total

async def acknowledge_alert(db: AsyncSession, alert_id: str, user_id: str):
    record = await db.get(AlertRecord, alert_id)
    if not record:
        return False, "预警不存在"
    record.is_acknowledged = True
    record.acknowledged_by = user_id
    record.acknowledged_at = datetime.utcnow()
    await db.commit()
    return True, "已确认"

async def resolve_alert(db: AsyncSession, alert_id: str):
    record = await db.get(AlertRecord, alert_id)
    if not record:
        return False, "预警不存在"
    record.is_resolved = True
    record.resolved_at = datetime.utcnow()
    await db.commit()
    return True, "已解决"

async def create_alert_rule(db: AsyncSession, name, alert_type, conditions, target_type=None, target_id=None, severity="warning", created_by=None):
    try:
        rule = AlertRule(name=name, alert_type=alert_type, target_type=target_type, target_id=target_id, conditions=conditions, severity=severity, created_by=created_by)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return True, "规则创建成功", rule
    except Exception as e:
        await db.rollback()
        return False, str(e), None

async def get_alert_rules(db: AsyncSession, alert_type=None, enabled_only=False):
    stmt = select(AlertRule)
    if alert_type:
        stmt = stmt.where(AlertRule.alert_type == alert_type)
    if enabled_only:
        stmt = stmt.where(AlertRule.enabled == True)
    stmt = stmt.order_by(AlertRule.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())
