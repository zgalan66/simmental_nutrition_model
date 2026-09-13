\
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.formula_tag_models import Tag

DEFAULT_TAGS = [
    {"name": "育肥期", "color": "#FF6B6B"},
    {"name": "妊娠期", "color": "#4ECDC4"},
    {"name": "泌乳期", "color": "#45B7D1"},
    {"name": "架子牛", "color": "#96CEB4"},
    {"name": "收藏", "color": "#FFEAA7"},
]

async def init_default_tags(db: AsyncSession):
    for td in DEFAULT_TAGS:
        existing = await db.execute(select(Tag).where(Tag.name == td["name"]))
        if not existing.scalar_one_or_none():
            db.add(Tag(**td))
    await db.commit()
