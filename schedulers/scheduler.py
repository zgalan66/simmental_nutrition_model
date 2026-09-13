"""
schedulers/scheduler.py — 定时任务
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import settings
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _check_price_job():
    logger.info("🔍 定时任务: 检测原料价格异常...")
    async with AsyncSessionLocal() as db:
        try:
            from services.alert_service import check_price_alerts
            triggered = await check_price_alerts(db)
            if triggered:
                logger.warning(f"  ⚠️ 触发 {len(triggered)} 条价格预警")
        except Exception as e:
            logger.error(f"  价格检测失败: {e}")


async def _check_nutrition_job():
    logger.info("🥗 定时任务: 检测营养不达标...")
    async with AsyncSessionLocal() as db:
        try:
            from services.alert_service import check_nutrition_alerts
            triggered = await check_nutrition_alerts(db)
            if triggered:
                logger.warning(f"  ⚠️ 触发 {len(triggered)} 条营养预警")
        except Exception as e:
            logger.error(f"  营养检测失败: {e}")


def start_scheduler():
    scheduler.add_job(
        _check_price_job,
        trigger=IntervalTrigger(hours=settings.PRICE_CHECK_INTERVAL_HOURS),
        id="price_check", name="原料价格异常检测", replace_existing=True,
    )
    scheduler.add_job(
        _check_nutrition_job,
        trigger=IntervalTrigger(hours=settings.NUTRITION_CHECK_INTERVAL_HOURS),
        id="nutrition_check", name="营养不达标检测", replace_existing=True,
    )
    scheduler.start()
    logger.info("  ✅ 定时任务已注册")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("  ✅ 定时任务已停止")
