import pytest
import pytest_asyncio

# 导入项目的数据库配置
from database import AsyncSessionLocal, init_db

# 导入所有模型（和 init_db 里保持一致）
from models.feed_models import Feed, FeedPriceHistory
from models.formula_models import Formula, FormulaVersion
from models.formula_tag_models import Tag, FormulaFavorite
from models.alert_models import AlertRule, AlertRecord


@pytest_asyncio.fixture
async def async_db():
    """异步 SQLAlchemy session fixture，复用项目数据库配置。"""
    # 确保表已创建
    await init_db()

    # 提供 session
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def db(async_db):
    """别名 fixture。"""
    return async_db