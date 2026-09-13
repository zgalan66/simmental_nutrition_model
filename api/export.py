from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote
from database import get_db
from services.export_service import export_formula_excel

router = APIRouter()


@router.get("/formula/{formula_id}", summary="导出配方为 Excel")
async def export_formula(formula_id: str, db: AsyncSession = Depends(get_db)):
    data = await export_formula_excel(db, formula_id)
    if data is None:
        raise HTTPException(404, "配方不存在")
    filename = f"formula_{formula_id[:8]}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
