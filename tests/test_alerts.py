\
import pytest
from services.alert_service import init_default_alert_rules

@pytest.mark.asyncio
async def test_init_default_rules(async_db):
    created = await init_default_alert_rules(async_db)
    assert created >= 0
