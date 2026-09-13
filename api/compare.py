from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.compare_service import compare_formulas

router = APIRouter()


@router.get("/", summary="对比两个配方")
async def compare(a: str, b: str, db: AsyncSession = Depends(get_db)):
    result = await compare_formulas(db, a, b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"success": True, "data": result}
