from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models.template_models import ConstraintTemplate


async def list_templates(db: AsyncSession, category: Optional[str] = None):
    stmt = select(ConstraintTemplate)
    if category:
        stmt = stmt.where(ConstraintTemplate.category == category)
    stmt = stmt.order_by(desc(ConstraintTemplate.is_default), ConstraintTemplate.name)
    r = await db.execute(stmt)
    return list(r.scalars().all())


async def get_template(db: AsyncSession, tid: str):
    return await db.get(ConstraintTemplate, tid)


async def create_template(db: AsyncSession, data: Dict[str, Any]):
    t = ConstraintTemplate(**data)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def update_template(db: AsyncSession, tid: str, data: Dict[str, Any]):
    t = await db.get(ConstraintTemplate, tid)
    if not t:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return t


async def delete_template(db: AsyncSession, tid: str) -> bool:
    t = await db.get(ConstraintTemplate, tid)
    if not t:
        return False
    await db.delete(t)
    await db.commit()
    return True
