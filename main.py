\
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db, engine, AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("🚀 启动西门塔尔公牛营养模型系统...")
    # 强制触发所有模型模块导入，确保表已注册到 Base.metadata
    from models import feed_models, formula_models, formula_tag_models, alert_models  # noqa
    from models.base import Base
    await init_db()
    # 兜底：再跑一次 create_all，确保关联表（如 formula_tags）已建
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("  ✅ 数据库表已就绪")

    async with AsyncSessionLocal() as db:
        from services.formula_tag_crud import init_default_tags
        await init_default_tags(db)
    logger.info("  ✅ 默认标签已就绪")

    async with AsyncSessionLocal() as db:
        from services.alert_service import init_default_alert_rules
        created = await init_default_alert_rules(db)
        if created > 0:
            logger.info(f"  ✅ 初始化了 {created} 条预警规则")

    if settings.ENABLE_SCHEDULER:
        from schedulers.scheduler import start_scheduler
        start_scheduler()
        logger.info("  ✅ 定时任务已启动")

    logger.info("🎉 系统启动完成!")
    yield
    logger.info("🛑 正在关闭系统...")
    if settings.ENABLE_SCHEDULER:
        from schedulers.scheduler import stop_scheduler
        stop_scheduler()

app = FastAPI(title="西门塔尔公牛营养模型系统", version="2.0.0", lifespan=lifespan)

# ✅ 开发期放开 CORS，允许 localhost:3000 / 8080 等前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.formulas import router as formulas_router
app.include_router(formulas_router, prefix="/api/v1/formulas", tags=["配方"])

from api.export import router as export_router
app.include_router(export_router, prefix="/api/v1/export", tags=["导出"])

from api.compare import router as compare_router
app.include_router(compare_router, prefix="/api/v1/compare", tags=["配方对比"])

from api.feeds import router as feeds_router
app.include_router(feeds_router, prefix="/api/v1/feeds", tags=["原料"])

from api.price import router as price_router
app.include_router(price_router, prefix="/api/v1/price", tags=["价格"])

from api.recommend import router as recommend_router
app.include_router(recommend_router, prefix="/api/v1/recommend", tags=["推荐"])

from api.templates import router as templates_router
app.include_router(templates_router, prefix="/api/v1/templates", tags=["约束模板"])

from api.tags_favorites import router as tags_router
app.include_router(tags_router, prefix="/api/v1", tags=["标签收藏"])

from api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["看板"])

from api.alerts import router as alerts_router
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["预警"])

from api.import_export import router as import_export_router
app.include_router(import_export_router, prefix="/api/v1/io", tags=["导入导出"])

from api.batch import router as batch_router
app.include_router(batch_router, prefix="/api/v1/batch", tags=["批量"])

from api.websocket import router as ws_router
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

from fastapi.responses import FileResponse as _FileResponse
if os.path.exists("web"):
    @app.get("/ui", include_in_schema=False)
    async def ui_page():
        return _FileResponse("web/index.html")

if os.path.exists("examples"):
    app.mount("/demo", StaticFiles(directory="examples"), name="demo")

@app.get("/")
async def root():
    return {"name": "西门塔尔公牛营养模型系统", "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
