\
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    # ✅ 修复：只导入真实存在的类，去掉 FormulaTag
    from models.feed_models import Feed, FeedPriceHistory
    from models.formula_models import Formula, FormulaVersion
    from models.formula_tag_models import Tag, FormulaFavorite
    from models.alert_models import AlertRule, AlertRecord
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
