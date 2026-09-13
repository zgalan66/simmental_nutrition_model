import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sqlalchemy import text
from database import engine

async def migrate():
    async with engine.begin() as conn:
        # 检查 feeds 表现在有哪些列
        result = await conn.execute(text("PRAGMA table_info(feeds)"))
        cols = {row[1] for row in result.fetchall()}
        print("现有列:", sorted(cols))

        needed = {
            "dm_pct": "FLOAT",
            "adf_pct": "FLOAT",
            "tdn_pct": "FLOAT",
            "ca_pct": "FLOAT",
            "p_pct": "FLOAT",
            "extra_json": "JSON",
        }
        for col, typ in needed.items():
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE feeds ADD COLUMN {col} {typ}"))
                print(f"  + 已添加列: {col}")
            else:
                print(f"  = 已存在: {col}")
    print("迁移完成")

if __name__ == "__main__":
    asyncio.run(migrate())