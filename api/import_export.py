\
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
router = APIRouter()
@router.post("/export")
async def export_excel(db: AsyncSession = Depends(get_db)):
    return {"success": True, "message": "Export endpoint"}
