\
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
router = APIRouter()
@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_db)):
    return {"data": [], "message": "Tags endpoint"}
