\
import pytest
from services.dashboard_service import get_dashboard_overview

@pytest.mark.asyncio
async def test_overview(async_db):
    data = await get_dashboard_overview(async_db)
    assert "total_formulas" in data
