\
#!/usr/bin/env python3
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine, init_db, AsyncSessionLocal
from config import settings

async def init_all():
    print("=" * 60)
    print("🐂 西门塔尔公牛营养模型系统 - 项目初始化")
    print("=" * 60)

    # 强制注册所有模型到 Base.metadata（避免导入时序导致表缺失）
    from models import feed_models, formula_models, formula_tag_models, alert_models  # noqa

    print("\n[1/4] 创建数据库表...")
    await init_db()
    print("  ✅ 所有表已创建")
    print("\n[2/4] 初始化默认标签...")
    async with AsyncSessionLocal() as db:
        # 兜底：确保标签相关表存在
        from models.base import Base
        from models.formula_tag_models import Tag, formula_tag_association
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from services.formula_tag_crud import init_default_tags
        await init_default_tags(db)
    print("  ✅ 默认标签已创建")
    print("\n[3/4] 初始化预警规则...")
    async with AsyncSessionLocal() as db:
        from services.alert_service import init_default_alert_rules
        created = await init_default_alert_rules(db)
        print(f"  ✅ {created} 条预警规则已创建")
    print("\n[4/4] 完成!")
    print("\n启动服务: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(init_all())
